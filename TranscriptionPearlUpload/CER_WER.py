# Import necessary libraries
import tkinter as tk              # For creating GUI dialogs
from tkinter import filedialog    # For file selection dialogs
import re, csv, os, string        # Basic Python utilities
import jiwer                      # For calculating WER and CER
from jiwer.transforms import AbstractTransform  # For custom text transformations
import difflib                    # For sequence comparison
from collections import Counter   # For counting error occurrences
import enchant                    # For spell checking
from Levenshtein import distance as levenshtein_distance  # For calculating edit distance
from itertools import zip_longest # For parallel iteration
import inflect                    # For handling word inflections
import nltk                       # For natural language processing
from nltk.stem import WordNetLemmatizer  # For word lemmatization

# Initialize required tools and resources
d = enchant.Dict("en_US")        # English dictionary for spell checking
p = inflect.engine()             # Tool for handling singular/plural forms
lemmatizer = WordNetLemmatizer() # Tool for finding base forms of words
nltk.download('wordnet', quiet=True)  # Download required NLTK data

class CustomTransform(AbstractTransform):
    """
    Custom transformation class that inherits from JiWER's AbstractTransform.
    Used to standardize text by removing extra whitespace while preserving content.
    """
    def process_string(self, s):
        return re.sub(r'\s+', ' ', s).strip()

def has_different_digits(word1, word2):
    """
    Check if two words contain different numerical digits.
    
    Args:
        word1 (str): First word to compare
        word2 (str): Second word to compare
    
    Returns:
        bool: True if words contain different digits, False otherwise
    """
    digits1 = re.findall(r'\d+', word1)
    digits2 = re.findall(r'\d+', word2)
    return digits1 != digits2

def is_spelling_correction(word1, word2):
    """
    Determines if the difference between two words is likely a spelling correction.
    
    Args:
        word1 (str): Original word (reference)
        word2 (str): Comparison word (hypothesis)
    
    Returns:
        bool: True if the difference appears to be a spelling correction, False otherwise
    """
    # Clean words by removing punctuation and converting to lowercase
    translator = str.maketrans('', '', string.punctuation)
    word1_clean = word1.translate(translator).lower()
    word2_clean = word2.translate(translator).lower()

    # Early return conditions
    if word1_clean == word2_clean:  # Words are identical after cleaning
        return False
    if not word1_clean or not word2_clean:  # Empty strings after cleaning
        return False
    if has_different_digits(word1, word2):  # Different numerical content
        return False

    # Check dictionary validity of both words
    word1_valid = d.check(word1_clean)
    word2_valid = d.check(word2_clean)

    # Check for proper nouns by testing capitalized versions
    if not word1_valid and not word2_valid:
        word1_cap = word1_clean.capitalize()
        word2_cap = word2_clean.capitalize()
        word1_valid = d.check(word1_cap)
        word2_valid = d.check(word2_cap)

    # Handle morphological variations (plurals, verb forms)
    if word1_valid and word2_valid and word1_clean != word2_clean:
        # Check for plural forms
        if p.singular_noun(word1_clean) == word2_clean or p.singular_noun(word2_clean) == word1_clean:
            return True
        
        # Check for different forms of the same word
        if lemmatizer.lemmatize(word1_clean) == lemmatizer.lemmatize(word2_clean):
            return True
        
        return False

    # If original word is valid but hypothesis isn't, it's an error
    if word1_valid and not word2_valid:
        return False

    # Calculate edit distance between words
    edit_distance = levenshtein_distance(word1_clean, word2_clean)
    max_len = max(len(word1_clean), len(word2_clean))
    min_len = min(len(word1_clean), len(word2_clean))

    # Apply length-based criteria for spelling corrections
    if max_len <= 2 and edit_distance <= 1:
        return False  # Very short words are likely intentional differences
    elif 3 <= max_len <= 5 and edit_distance <= 1:
        return True
    elif 6 <= max_len <= 8 and edit_distance <= 2:
        return True
    elif max_len > 8 and edit_distance <= 3:
        return True

    # Additional checks for potential spelling errors
    if abs(len(word1_clean) - len(word2_clean)) > 3:  # Length difference too large
        return False
    if word1_clean[0] != word2_clean[0] and word1_clean[-1] != word2_clean[-1]:  # Both ends different
        return False

    # Check for common beginning or ending sequences
    common_prefix_len = len(os.path.commonprefix([word1_clean, word2_clean]))
    common_suffix_len = len(os.path.commonprefix([word1_clean[::-1], word2_clean[::-1]]))
    if common_prefix_len < 2 and common_suffix_len < 2:
        return False

    return True

def is_capitalization_error(word1, word2):
    """
    Checks if two words differ only in capitalization.
    
    Args:
        word1 (str): First word
        word2 (str): Second word
    
    Returns:
        bool: True if words differ only in capitalization
    """
    return word1.lower() == word2.lower() and word1 != word2

def is_punctuation_error(word1, word2):
    """
    Checks if two words differ only in punctuation.
    
    Args:
        word1 (str): First word
        word2 (str): Second word
    
    Returns:
        bool: True if words differ only in punctuation
    """
    word1_stripped = re.sub(r'[^\w\s]', '', word1)
    word2_stripped = re.sub(r'[^\w\s]', '', word2)
    return word1_stripped.lower() == word2_stripped.lower() and word1 != word2
def count_words(text):
    """
    Counts the number of words in a text after standardizing spacing.
    
    Args:
        text (str): Input text to count words from
    
    Returns:
        int: Number of words in the text
    """
    transformation = CustomTransform()
    transformed_text = transformation(text)
    return len(transformed_text.split())

def is_combined_cap_punct_error(word1, word2):
    """
    Checks if two words differ only in capitalization and/or punctuation.
    
    Args:
        word1 (str): First word
        word2 (str): Second word
    
    Returns:
        bool: True if differences are only in capitalization/punctuation
    """
    word1_stripped = re.sub(r'[^\w\s]', '', word1)
    word2_stripped = re.sub(r'[^\w\s]', '', word2)
    return (word1_stripped.lower() == word2_stripped.lower() and 
            word1 != word2 and 
            not has_different_digits(word1, word2))

def calculate_wer_cer(reference, hypothesis, mode):
    """
    Calculates Word Error Rate (WER) and Character Error Rate (CER) between reference and hypothesis texts.
    Also identifies and categorizes different types of errors.
    
    Args:
        reference (str): Original reference text
        hypothesis (str): Hypothesis text to compare
        mode (str): 'S' for strict mode or 'M' for modified mode
    
    Returns:
        tuple: (WER score, CER score, detailed errors counter, ignored errors counter)
    """
    # Initialize transformation and process texts
    transformation = CustomTransform()
    reference_transformed = transformation(reference)
    hypothesis_transformed = transformation(hypothesis)

    # Validate input
    if not reference_transformed or not hypothesis_transformed:
        print("Error: After transformation, one or both texts are empty.")
        return None, None, None, None

    # Split into words
    reference_words = reference_transformed.split()
    hypothesis_words = hypothesis_transformed.split()

    print(f"Reference length: {len(reference_words)}")
    print(f"Hypothesis length: {len(hypothesis_words)}")

    # Initialize error counters
    detailed_errors = Counter()
    ignored_errors = Counter()

    # Use sequence matcher to find differences
    matcher = difflib.SequenceMatcher(None, reference_words, hypothesis_words)

    reference_modified = []
    hypothesis_modified = []
    
    # Process each difference found by the sequence matcher
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':  # Words match exactly
            reference_modified.extend(reference_words[i1:i2])
            hypothesis_modified.extend(hypothesis_words[j1:j2])
        elif tag == 'replace':  # Words are different
            for ref_word, hyp_word in zip_longest(reference_words[i1:i2], hypothesis_words[j1:j2], fillvalue=''):
                if ref_word == hyp_word:
                    reference_modified.append(ref_word)
                    hypothesis_modified.append(hyp_word)
                # In modified mode, check for acceptable variations
                elif mode == 'M' and (is_combined_cap_punct_error(ref_word, hyp_word) or
                                    is_capitalization_error(ref_word, hyp_word) or
                                    is_punctuation_error(ref_word, hyp_word) or
                                    is_spelling_correction(ref_word, hyp_word)):
                    ignored_errors[(ref_word, hyp_word, "Ignored")] += 1
                    reference_modified.append(ref_word)
                    hypothesis_modified.append(ref_word)
                else:
                    detailed_errors[(ref_word, hyp_word)] += 1
                    reference_modified.append(ref_word)
                    hypothesis_modified.append(hyp_word)
        elif tag == 'delete':  # Words in reference but not in hypothesis
            for ref_word in reference_words[i1:i2]:
                detailed_errors[(ref_word, '<deleted>')] += 1
                reference_modified.append(ref_word)
        elif tag == 'insert':  # Words in hypothesis but not in reference
            for hyp_word in hypothesis_words[j1:j2]:
                detailed_errors[('<inserted>', hyp_word)] += 1
                hypothesis_modified.append(hyp_word)

    # Calculate final WER and CER
    reference_modified_text = ' '.join(reference_modified)
    hypothesis_modified_text = ' '.join(hypothesis_modified)

    try:
        wer_score = jiwer.wer(reference_modified_text, hypothesis_modified_text)
        cer_score = jiwer.cer(reference_modified_text, hypothesis_modified_text)
    except ValueError as e:
        print(f"Error calculating WER/CER: {e}")
        wer_score = None
        cer_score = None

    return wer_score, cer_score, detailed_errors, ignored_errors

def select_file(title):
    """
    Creates a file selection dialog.
    
    Args:
        title (str): Title for the dialog window
    
    Returns:
        str: Selected file path
    """
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title=title, filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
    return file_path

def select_directory(title):
    """
    Creates a directory selection dialog.
    
    Args:
        title (str): Title for the dialog window
    
    Returns:
        str: Selected directory path
    """
    root = tk.Tk()
    root.withdraw()
    directory = filedialog.askdirectory(title=title)
    return directory

def process_directory(directory_path, master_text, master_word_count, mode):
    """
    Processes all subdirectories containing text files for analysis.
    
    Args:
        directory_path (str): Path to main directory
        master_text (str): Reference text content
        master_word_count (int): Word count of reference text
        mode (str): Analysis mode ('S' or 'M')
    """
    for root, dirs, files in os.walk(directory_path):
        hypothesis_files = [f for f in files if f.endswith('.txt') and f != 'analysis_results.txt']
        
        if hypothesis_files:
            print(f"\nProcessing folder: {root}")
            process_subfolder(root, master_text, master_word_count, mode)

def read_file(file_path):
    """
    Reads and returns the content of a text file.
    
    Args:
        file_path (str): Path to the file
    
    Returns:
        str: File content or None if error occurs
    """
    if not file_path:
        print("No file selected.")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        if not content.strip():
            print(f"Warning: The file {file_path} is empty.")
        return content
    except UnicodeDecodeError:
        print(f"Error: Unable to read {file_path} in UTF-8 encoding. Please ensure the file is in UTF-8 format.")
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return None

def write_error_rates_csv(subfolder_path, wer_cer_data):
    """
    Writes WER and CER rates to a CSV file.
    
    Args:
        subfolder_path (str): Path to save the CSV file
        wer_cer_data (list): List of tuples containing WER and CER values
    """
    csv_path = os.path.join(subfolder_path, "error_rates.csv")
    
    headers = ["Error_Rate"] + [str(i) for i in range(1, len(wer_cer_data) + 1)]
    wer_row = ["WER"] + [f"{wer:.2%}" if wer is not None else "N/A" for wer, _ in wer_cer_data]
    cer_row = ["CER"] + [f"{cer:.2%}" if cer is not None else "N/A" for _, cer in wer_cer_data]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(wer_row)
        writer.writerow(cer_row)
    
    print(f"Error rates saved to {csv_path}")

def strict_accuracy_check(master_word_count, detailed_errors):
    """
    Performs strict accuracy checking of transcription errors without ignoring any differences.
    
    Args:
        master_word_count (int): Total word count in the reference text
        detailed_errors (Counter): Counter object containing error details
    
    Returns:
        dict: Dictionary containing:
            - substitutions: Number of word substitutions
            - insertions: Number of word insertions
            - deletions: Number of word deletions
            - correct: Number of correct words
            - total_reference: Total words in reference text
            - total_recognized: Total words in recognized text
            - alignment_length: Length of aligned text
            - ref_word_check: Boolean indicating reference word count validation
            - rec_word_check: Boolean indicating recognized word count validation
            - sum_check: Boolean indicating alignment length validation
    """
    # Calculate different types of errors
    substitutions = sum(count for (ref, hyp), count in detailed_errors.items() 
                       if ref != '<inserted>' and hyp != '<deleted>')
    insertions = sum(count for (ref, hyp), count in detailed_errors.items() 
                    if ref == '<inserted>')
    deletions = sum(count for (ref, hyp), count in detailed_errors.items() 
                   if hyp == '<deleted>')
    
    # Calculate correct words and total recognized words
    correct = master_word_count - (substitutions + deletions)
    total_recognized = master_word_count + insertions - deletions

    # Perform verification checks
    alignment_length = correct + substitutions + deletions + insertions
    ref_word_check = correct + substitutions + deletions == master_word_count
    rec_word_check = correct + substitutions + insertions == total_recognized
    sum_check = substitutions + deletions + insertions + correct == alignment_length

    return {
        "substitutions": substitutions,
        "insertions": insertions,
        "deletions": deletions,
        "correct": correct,
        "total_reference": master_word_count,
        "total_recognized": total_recognized,
        "alignment_length": alignment_length,
        "ref_word_check": ref_word_check,
        "rec_word_check": rec_word_check,
        "sum_check": sum_check
    }

def modified_accuracy_check(master_word_count, detailed_errors, ignored_errors):
    """
    Performs modified accuracy checking of transcription errors, accounting for ignored differences.
    
    Args:
        master_word_count (int): Total word count in the reference text
        detailed_errors (Counter): Counter object containing error details
        ignored_errors (Counter): Counter object containing ignored error details
    
    Returns:
        dict: Dictionary containing:
            - substitutions: Number of word substitutions
            - insertions: Number of word insertions
            - deletions: Number of word deletions
            - ignored: Number of ignored differences
            - correct: Number of correct words
            - total_reference: Total words in reference text
            - total_recognized: Total words in recognized text
            - alignment_length: Length of aligned text
            - ref_word_check: Boolean indicating reference word count validation
            - rec_word_check: Boolean indicating recognized word count validation
            - sum_check: Boolean indicating alignment length validation
    """
    # Calculate different types of errors
    substitutions = sum(count for (ref, hyp), count in detailed_errors.items() 
                       if ref != '<inserted>' and hyp != '<deleted>')
    insertions = sum(count for (ref, hyp), count in detailed_errors.items() 
                    if ref == '<inserted>')
    deletions = sum(count for (ref, hyp), count in detailed_errors.items() 
                   if hyp == '<deleted>')
    ignored = sum(ignored_errors.values())
    
    # Calculate correct words and total recognized words
    correct = master_word_count - (substitutions + deletions + ignored)
    total_recognized = master_word_count + insertions - deletions

    # Perform verification checks
    alignment_length = correct + substitutions + deletions + insertions + ignored
    ref_word_check = correct + substitutions + deletions + ignored == master_word_count
    rec_word_check = correct + substitutions + insertions + ignored == total_recognized
    sum_check = substitutions + deletions + insertions + correct + ignored == alignment_length

    return {
        "substitutions": substitutions,
        "insertions": insertions,
        "deletions": deletions,
        "ignored": ignored,
        "correct": correct,
        "total_reference": master_word_count,
        "total_recognized": total_recognized,
        "alignment_length": alignment_length,
        "ref_word_check": ref_word_check,
        "rec_word_check": rec_word_check,
        "sum_check": sum_check
    }

def process_subfolder(subfolder_path, master_text, master_word_count, mode):
    """
    Processes all text files in a subfolder, calculating error rates and generating reports.
    
    Args:
        subfolder_path (str): Path to the subfolder containing hypothesis files
        master_text (str): Reference text content
        master_word_count (int): Word count of reference text
        mode (str): Analysis mode ('S' or 'M')
    """
    # Get list of hypothesis files, excluding results file
    hypothesis_files = [f for f in os.listdir(subfolder_path) 
                       if f.endswith('.txt') and f != 'analysis_results.txt']    
    hypothesis_files.sort()

    results = []
    all_ignored_errors = Counter()
    wer_cer_data = []

    # Process each hypothesis file
    for i, hypothesis_file in enumerate(hypothesis_files[:10], 1):
        hypothesis_path = os.path.join(subfolder_path, hypothesis_file)
        hypothesis_text = read_file(hypothesis_path)

        if hypothesis_text is None:
            continue

        print(f"\nProcessing file {i}: {hypothesis_file}")
        wer, cer, detailed_errors, ignored_errors = calculate_wer_cer(master_text, 
                                                                    hypothesis_text, 
                                                                    mode)

        # Store WER and CER data
        wer_cer_data.append((wer, cer))

        # Save detailed errors to CSV
        error_csv_file = os.path.join(subfolder_path, f"Results_{i}.csv")
        with open(error_csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Original Word', 'Error Word', 'Number of Occurrences'])
            for (ref_segment, hyp_segment), count in detailed_errors.items():
                writer.writerow([ref_segment, hyp_segment, count])

        print(f"Errors saved to {error_csv_file}")

        # Save ignored errors if in modified mode
        if mode == 'M':
            ignored_errors_file = os.path.join(subfolder_path, f"Ignored_Errors_{i}.csv")
            with open(ignored_errors_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Original Word', 'Error Word', 'Error Type', 
                               'Number of Occurrences'])
                for (ref_word, hyp_word, error_type), count in ignored_errors.items():
                    writer.writerow([ref_word, hyp_word, error_type, count])
            print(f"Ignored errors saved to {ignored_errors_file}")

        all_ignored_errors.update(ignored_errors)
    
        # Perform accuracy check based on mode
        if mode == 'S':
            accuracy_check = strict_accuracy_check(master_word_count, detailed_errors)
        else:  # mode == 'M'
            accuracy_check = modified_accuracy_check(master_word_count, detailed_errors, 
                                                  ignored_errors)

        # Format results
        result = f"Results for {hypothesis_file}:\n"
        if wer is not None:
            result += f"Word Error Rate (WER): {wer:.2%}\n"
        if cer is not None:
            result += f"Character Error Rate (CER): {cer:.2%}\n"
        result += f"Total errors: {sum(detailed_errors.values())}\n"
        result += f"Substitutions: {accuracy_check['substitutions']}\n"
        result += f"Insertions: {accuracy_check['insertions']}\n"
        result += f"Deletions: {accuracy_check['deletions']}\n"
        if mode == 'M':
            result += f"Ignored errors: {accuracy_check['ignored']}\n"
        result += f"Correct words: {accuracy_check['correct']}\n"
        result += f"Total words in reference: {accuracy_check['total_reference']}\n"
        result += f"Total words in recognized: {accuracy_check['total_recognized']}\n"
        result += f"Alignment length: {accuracy_check['alignment_length']}\n"
        result += f"Reference word check: {'Passed' if accuracy_check['ref_word_check'] else 'Failed'}\n"
        result += f"Recognized word check: {'Passed' if accuracy_check['rec_word_check'] else 'Failed'}\n"
        result += f"Sum check: {'Passed' if accuracy_check['sum_check'] else 'Failed'}\n"

        results.append(result)
        print(result)

    # Save all results to a file
    output_file = os.path.join(subfolder_path, "analysis_results.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n*****\n".join(results))
        f.write(f"\n\nTotal words in master document: {master_word_count}")
    
    # Write error rates CSV
    write_error_rates_csv(subfolder_path, wer_cer_data)

    print(f"\nAll results for subfolder {subfolder_path} have been saved to {output_file}")

    # Save all ignored errors to a single CSV file in modified mode
    if mode == 'M':
        ignored_errors_file = os.path.join(subfolder_path, "all_error_types.csv")
        with open(ignored_errors_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Original Word', 'Error Word', 'Error Type', 
                           'Number of Occurrences'])
            for (ref_word, hyp_word, error_type), count in all_ignored_errors.items():
                writer.writerow([ref_word, hyp_word, error_type, count])
        print(f"All ignored errors saved to {ignored_errors_file}")

def main():
    """
    Main function that orchestrates the entire analysis process.
    Handles user input, file selection, and initiates analysis.
    """
    # Get analysis mode from user
    mode = input("Enter 'S' for Strict mode or 'M' for Modified mode: ").upper()
    while mode not in ['S', 'M']:
        mode = input("Invalid input. Please enter 'S' for Strict mode or 'M' for Modified mode: ").upper()

    # Select and read master text file
    print("Select the master text file:")
    master_file = select_file("Select Master Text File")
    master_text = read_file(master_file)

    if master_text is None:
        return

    # Count words in master text
    master_word_count = count_words(master_text)

    # Select directory with hypothesis files
    print("Select the directory containing subfolders with hypothesis text files:")
    hypothesis_directory = select_directory("Select Hypothesis Directory")

    if not hypothesis_directory:
        print("No directory selected.")
        return

    # Process all files in directory
    process_directory(hypothesis_directory, master_text, master_word_count, mode)

    print(f"\nTotal words in master document: {master_word_count}")

if __name__ == "__main__":
    main()