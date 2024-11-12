import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import pandas as pd
import fitz, re, base64, os, shutil, time, asyncio, string, json
from PIL import Image, ImageTk, ImageOps
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# # Import Local Scripts
from util.subs.ImageSplitter import ImageSplitter

# OpenAI API
from openai import OpenAI
import openai

# Antrhopic API
from anthropic import AsyncAnthropic # Parallel API Calls
import anthropic

# Google API
import google.generativeai as genai

from google.generativeai.types import HarmCategory, HarmBlockThreshold

class App(TkinterDnD.Tk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Transcription Pearl 1.0 beta")  # Set the window title
        self.link_nav = 0
        self.geometry("1200x800")

        if os.name == 'nt':  # For Windows use the .ico file
            try:
                self.iconbitmap("util/pb.ico")
            except:
                pass  # If icon file is not found, use default icon

        # Flags, Toggles, and Variables
        self.save_toggle = False
        self.find_replace_toggle = False
        self.original_image = None
        self.photo_image = None
        self.current_scale = 1    

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Top frame
        self.grid_rowconfigure(1, weight=1)  # Main frame
        self.grid_rowconfigure(2, weight=0)  # Bottom frame

        self.top_frame = tk.Frame(self)
        self.top_frame.grid(row=0, column=0, sticky="nsew")
 
        self.top_frame.grid_columnconfigure(0, weight=0)
        self.top_frame.grid_columnconfigure(1, weight=1)
        self.top_frame.grid_columnconfigure(2, weight=0)
        self.top_frame.grid_columnconfigure(3, weight=0)
        self.top_frame.grid_columnconfigure(4, weight=0)
        self.top_frame.grid_columnconfigure(5, weight=0)

        text_label = tk.Label(self.top_frame, text="Displayed Text:")
        text_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.text_type_label = tk.Label(self.top_frame, text="None")
        self.text_type_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        self.button1 = tk.Button(self.top_frame, text="<<", command=lambda: self.navigate_images(-2))
        self.button1.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        self.button2 = tk.Button(self.top_frame, text="<", command=lambda: self.navigate_images(-1))
        self.button2.grid(row=0, column=3, sticky="e", padx=5, pady=5)

        self.page_counter_var = tk.StringVar()
        self.page_counter_var.set("0 / 0")

        page_counter_label = tk.Label(self.top_frame, textvariable=self.page_counter_var)
        page_counter_label.grid(row=0, column=4, sticky="e", padx=5, pady=5)

        self.button4 = tk.Button(self.top_frame, text=">", command=lambda: self.navigate_images(1))
        self.button4.grid(row=0, column=5, sticky="e", padx=5, pady=5)

        self.button5 = tk.Button(self.top_frame, text=">>", command=lambda: self.navigate_images(2))
        self.button5.grid(row=0, column=6, sticky="e", padx=5, pady=5)

        self.main_frame = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_frame.grid(row=1, column=0, sticky="nsew")

        self.text_display = self.create_text_widget(self.main_frame, "File to Edit", state="normal")
        self.image_display = tk.Canvas(self.main_frame, borderwidth=2, relief="groove")
        self.image_display.create_image(0, 0, anchor="nw", image=self.photo_image)

        self.main_frame.add(self.text_display)
        self.main_frame.add(self.image_display)

        self.bottom_frame = tk.Frame(self)
        self.bottom_frame.grid_rowconfigure(0, weight=1)
        self.bottom_frame.grid(row=2, column=0, sticky="nsew")

        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(1, weight=1)

        button_frame = tk.Frame(self.bottom_frame)
        button_frame.grid(row=0, column=0, sticky="nsw")

        button_frame.grid_columnconfigure(0, weight=0)
        button_frame.grid_columnconfigure(1, weight=0)
        button_frame.grid_columnconfigure(2, weight=1)
        button_frame.grid_rowconfigure(0, weight=1)
        button_frame.grid_rowconfigure(1, weight=1)
        button_frame.grid_rowconfigure(2, weight=1)
        button_frame.grid_rowconfigure(3, weight=1)

        textbox_frame = tk.Frame(self.bottom_frame)
        textbox_frame.grid(row=0, column=1, sticky="nsew")

        textbox_frame.grid_columnconfigure(0, weight=0)
        textbox_frame.grid_columnconfigure(1, weight=1)
        textbox_frame.grid_rowconfigure(0, weight=1)
        textbox_frame.grid_rowconfigure(1, weight=1)
        textbox_frame.grid_rowconfigure(2, weight=1)
       
        # Initialize initial settings 
        self.initialize_temp_directory()
        self.enable_drag_and_drop() 
        self.create_menus()
        self.create_key_bindings()
        self.bind_key_universal_commands(self.text_display)
        self.initialize_settings()

    def create_menus(self):
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)
        
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)

        self.process_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Process", menu=self.process_menu)
        
        self.file_menu.add_command(label="New Project", command=self.create_new_project)
        self.file_menu.add_command(label="Open Project", command=self.open_project)
        self.file_menu.add_command(label="Save Project As...", command=self.save_project_as)
        self.file_menu.add_command(label="Save Project", command=self.save_project)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Import Images Only", command=lambda: self.open_folder(toggle="Images without Text"))        
        self.file_menu.add_command(label="Import Text and Images", command=lambda: self.open_folder(toggle="Images with Text"))        
        self.file_menu.add_command(label="Import PDF", command=self.open_pdf)

        self.file_menu.add_separator()

        self.file_menu.add_command(label="Export", command=self.manual_export)

        self.file_menu.add_separator()

        self.file_menu.add_command(label="Settings", command=self.create_settings_window)

        self.file_menu.add_separator()

        self.file_menu.add_command(label="Exit", command=self.quit)

        self.edit_menu.add_command(label="Undo", command=self.undo)
        self.edit_menu.add_command(label="Redo", command=self.redo)

        self.edit_menu.add_separator()

        self.edit_menu.add_command(label="Cut", command=self.cut)
        self.edit_menu.add_command(label="Copy", command=self.copy)
        self.edit_menu.add_command(label="Paste", command=self.paste)

        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Rotate Image Clockwise", command=lambda: self.rotate_image("clockwise"))
        self.edit_menu.add_command(label="Rotate Image Counter-clockwise", command=lambda: self.rotate_image("counter-clockwise"))

        self.edit_menu.add_separator()

        self.edit_menu.add_command(label="Revert Current Page", command=self.revert_current_page)
        self.edit_menu.add_command(label="Revert All Pages", command=self.revert_all_pages)

        self.edit_menu.add_separator()

        self.edit_menu.add_command(label="Find and Replace", command=self.find_and_replace)

        self.edit_menu.add_separator()

        self.edit_menu.add_command(label="Edit Current Image", command=self.edit_single_image)
        self.edit_menu.add_command(label="Edit All Images", command=self.edit_all_images)

        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Delete Current Image", command=self.delete_current_image)

        self.process_menu.add_command(label="Recognize Text on Current Page", command=lambda: self.ai_function(all_or_one_flag="Current Page", ai_job="HTR"))        
        self.process_menu.add_command(label="Recognize Text on All Pages", command=lambda: self.ai_function(all_or_one_flag="All Pages", ai_job="HTR")) 

        self.process_menu.add_separator()

        self.process_menu.add_command(label="Correct Text on Current Page", command=lambda: self.ai_function(all_or_one_flag="Current Page", ai_job="Correct"))
        self.process_menu.add_command(label="Correct Text on All Pages", command=lambda: self.ai_function(all_or_one_flag="All Pages", ai_job="Correct"))

    def create_key_bindings(self):
        # Navigation bindings
        self.bind("<Control-Home>", lambda event: self.navigate_images(-2))
        self.bind("<Control-Left>", lambda event: self.navigate_images(-1))
        self.bind("<Control-Right>", lambda event: self.navigate_images(1))
        self.bind("<Control-End>", lambda event: self.navigate_images(2))

        # Rotation bindings
        self.bind("<Control-bracketright>", lambda event: self.rotate_image("clockwise"))
        self.bind("<Control-bracketleft>", lambda event: self.rotate_image("counter-clockwise"))

        # Project management bindings
        self.bind("<Control-n>", lambda event: self.create_new_project())  # Fixed missing angle brackets
        self.bind("<Control-e>", lambda event: self.export())  # Fixed syntax and missing angle brackets
        self.bind("<Control-s>", lambda event: self.save_project())  # Added parentheses for method call
        self.bind("<Control-o>", lambda event: self.open_project())  # Added parentheses for method call

        # Edit bindings
        self.bind("<Control-z>", lambda event: self.undo())  # Added parentheses for method call
        self.bind("<Control-y>", lambda event: self.redo())  # Added parentheses for method call

        # Find and Replace bindings
        self.bind("<Control-f>", lambda event: self.find_and_replace())  # Added parentheses for method call

        # Clipboard bindings
        self.bind("<Control-c>", lambda event: self.copy())  # Added parentheses for method call
        self.bind("<Control-x>", lambda event: self.cut())  # Added parentheses for method call
        self.bind("<Control-v>", lambda event: self.paste())  # Added parentheses for method call

        # Revert bindings
        self.bind("<Control-r>", lambda event: self.revert_current_page())  # Added parentheses for method call
        self.bind("<Control-Shift-r>", lambda event: self.revert_all_pages())  # Added parentheses for method call

        # Image management bindings
        self.bind("<Control-d>", lambda event: self.delete_current_image())  # Added parentheses for method call
        self.bind("<Control-i>", lambda event: self.edit_single_image())  # Added parentheses for method call
        self.bind("<Control-Shift-i>", lambda event: self.edit_all_images())  # Added parentheses for method call

        # AI function bindings
        self.bind("<Control-1>", lambda event: self.ai_function(all_or_one_flag="Current Page", ai_job="HTR"))
        self.bind("<Control-Shift-1>", lambda event: self.ai_function(all_or_one_flag="All Pages", ai_job="HTR"))
        self.bind("<Control-2>", lambda event: self.ai_function(all_or_one_flag="Current Page", ai_job="Correct"))
        self.bind("<Control-Shift-2>", lambda event: self.ai_function(all_or_one_flag="All Pages", ai_job="Correct"))

        # Mouse bindings
        self.image_display.bind("<Control-MouseWheel>", self.zoom)
        self.image_display.bind("<MouseWheel>", self.scroll)
        self.image_display.bind("<ButtonPress-1>", self.start_pan)
        self.image_display.bind("<B1-Motion>", self.pan)

    def create_image_widget(self, frame, image_path, state):
        # Load the image
        original_image = Image.open(image_path)
        self.photo_image = ImageTk.PhotoImage(original_image)

        # Create a canvas and add the image to it
        self.canvas = tk.Canvas(frame, borderwidth=2, relief="groove")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo_image)
        self.canvas.grid(sticky="nsew")

        # Bind zoom and scroll events
        self.canvas.bind("<Control-MouseWheel>", self.zoom)
        self.canvas.bind("<MouseWheel>", self.scroll)

        return self.canvas

    def create_text_widget(self, frame, label_text, state):
        # Create a Text widget to display the contents of the selected file
        text_display = tk.Text(frame, wrap="word", state=state, undo=True)
        # Make the font size 16
        text_display.config(font=("Arial", 12))
        
        text_display.grid(sticky="nsew")

        return text_display

    def bind_key_universal_commands(self, text_widget):
        text_widget.bind('<Control-h>', self.find_and_replace)
        text_widget.bind('<Control-f>', self.find_and_replace)
        text_widget.bind('<Control-z>', self.undo)
        text_widget.bind('<Control-y>', self.redo)

# Initialize Settings Functions

    def initialize_settings(self):   
        # Get the appropriate app data directory
        if os.name == 'nt':  # Windows
            app_data = os.path.join(os.environ['APPDATA'], 'TranscriptionPearl')
        else:  # Linux/Mac
            app_data = os.path.join(os.path.expanduser('~'), '.transcriptionpearl')
        
        # Create the directory if it doesn't exist
        os.makedirs(app_data, exist_ok=True)
        
        # Define settings file path
        self.settings_file_path = os.path.join(app_data, 'settings.json')
        
        # Initialize other settings...
        self.main_df = pd.DataFrame(columns=["Index", "Page", "Original_Text", "Initial_Draft_Text", 
                                        "Final_Draft", "Image_Path", "Text_Path", "Text_Toggle"])
        
        # First set default values
        self.restore_defaults()
        
        # Define model list
        self.model_list = [
            "gpt-4o",
            "gpt-4o-2024-08-06",
            "gpt-4o-mini",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "gemini-1.5-flash-001",
            "gemini-1.5-flash-002",
            "gemini-1.5-pro-001",
            "gemini-1.5-pro-002"
        ]

        # Check if settings file exists and load it
        if os.path.exists(self.settings_file_path):
            self.load_settings()
  
    def initialize_temp_directory(self):
        self.temp_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "util", "temp")
        self.images_directory = os.path.join(self.temp_directory, "images")

        # Clear the temp directory if it exists
        if os.path.exists(self.temp_directory):
            try:
                shutil.rmtree(self.temp_directory)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear temp directory: {e}")
                self.error_logging(f"Failed to clear temp directory: {e}")

        # Recreate the temp and images directories
        try:
            os.makedirs(self.temp_directory, exist_ok=True)
            os.makedirs(self.images_directory, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create temp directories: {e}")
            self.error_logging(f"Failed to create temp directories: {e}")

        # Reset the main DataFrame
        self.main_df = pd.DataFrame(columns=["Index", "Page", "Original_Text", "Initial_Draft_Text", "Final_Draft", "Image_Path", "Text_Path", "Text_Toggle"])
        self.page_counter = 0

# Settings Window

    def create_settings_window(self):
        self.toggle_button_state()
        self.settings_window = tk.Toplevel(self)
        self.settings_window.title("Settings")
        self.settings_window.geometry("1200x875")
        self.settings_window.attributes("-topmost", True)
        self.settings_window.protocol("WM_DELETE_WINDOW", lambda: self.on_settings_window_close(self.settings_window))

        self.settings_window.grid_columnconfigure(0, weight=1)
        self.settings_window.grid_columnconfigure(1, weight=4)
        self.settings_window.grid_rowconfigure(0, weight=1)

        left_frame = tk.Frame(self.settings_window)
        left_frame.grid(row=0, column=0, sticky="nsew")

        right_frame = tk.Frame(self.settings_window)
        right_frame.grid(row=0, column=1, sticky="nsew")

        # Left menu
        menu_options = [
            "APIs and Login Settings",
            "HTR Settings",
            "Correct Text Settings",
            "",
            "Load Settings",
            "Save Settings",
            "Restore Defaults",
            "Done"
        ]

        for i, option in enumerate(menu_options):
            if option == "":
                # Add an empty label with a specific height to create space above the "Load Settings" button
                empty_label = tk.Label(left_frame, text="", height=26)
                empty_label.grid(row=i, column=0)
            else:
                button = tk.Button(left_frame, text=option, width=30, command=lambda opt=option: self.show_settings(opt, right_frame))
                button.grid(row=i, column=0, padx=10, pady=5, sticky="w")

        # Right frame
        self.show_settings("General Settings", right_frame)
    
    def show_settings(self, option, frame):
        for widget in frame.winfo_children():
            widget.destroy()
        if option == "APIs and Login Settings":
            self.show_api_settings(frame)
        elif option == "HTR Settings":
            self.show_HTR_settings(frame)
        elif option == "Correct Text Settings":
            self.show_correct_text_settings(frame)
        elif option == "Load Settings":
            self.load_settings()
        elif option == "Save Settings":
            self.save_settings()
        elif option == "Restore Defaults":
            self.restore_defaults()
        elif option == "Done":
            self.on_settings_window_close(self.settings_window)

    def show_api_settings(self, frame):
            # OpenAI
            openai_label = tk.Label(frame, text="OpenAI API Key:")
            openai_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            self.openai_entry = tk.Entry(frame, width=130)
            self.openai_entry.insert(0, self.openai_api_key)
            self.openai_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="w")
            self.openai_entry.bind("<KeyRelease>", lambda event: setattr(self, 'openai_api_key', self.openai_entry.get()))
    
            # Anthropic
            anthropic_label = tk.Label(frame, text="Anthropic API Key:")
            anthropic_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
            self.anthropic_entry = tk.Entry(frame, width=130)
            self.anthropic_entry.insert(0, self.anthropic_api_key)
            self.anthropic_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
            self.anthropic_entry.bind("<KeyRelease>", lambda event: setattr(self, 'anthropic_api_key', self.anthropic_entry.get()))

            # Google

            google_api_key_label = tk.Label(frame, text="Google API Key:")
            google_api_key_label.grid(row=11, column=0, padx=10, pady=5, sticky="w")
            self.google_api_key_entry = tk.Entry(frame, width=130)
            self.google_api_key_entry.insert(0, self.google_api_key)
            self.google_api_key_entry.grid(row=11, column=1, columnspan=3, padx=10, pady=5, sticky="w")
            self.google_api_key_entry.bind("<KeyRelease>", lambda event: setattr(self, 'google_api_key', self.google_api_key_entry.get()))

    def show_HTR_settings(self, frame):
        explanation_label = tk.Label(frame, text=f"""The HTR function sends each image to the API simultaneously and asks it to transcribe the material.""", wraplength=675, justify=tk.LEFT)
       
        explanation_label.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        
        model_label = tk.Label(frame, text="Select model for HTR:")
        model_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.HTR_model_var = tk.StringVar(value=self.HTR_model)
        dropdown = ttk.Combobox(frame, textvariable=self.HTR_model_var, values=self.model_list, state="readonly", width=30)
        dropdown.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        # Update the model variable when the dropdown is changed
        dropdown.bind("<<ComboboxSelected>>", lambda event: setattr(self, 'HTR_model', dropdown.get()))

        general_label = tk.Label(frame, text="General Instructions:")
        general_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.HTR_general_entry = tk.Text(frame, height=5, width=60, wrap=tk.WORD)
        self.HTR_general_entry.insert(tk.END, self.HTR_system_prompt)
        self.HTR_general_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        # Update the general instructions when the text is changed
        self.HTR_general_entry.bind("<KeyRelease>", lambda event: setattr(self, 'HTR_system_prompt', self.HTR_system_prompt.get("1.0", tk.END)))

        general_scrollbar = tk.Scrollbar(frame, command=self.HTR_general_entry.yview)
        general_scrollbar.grid(row=2, column=2, sticky="ns")
        self.HTR_general_entry.config(yscrollcommand=general_scrollbar.set)

        detailed_label = tk.Label(frame, text="Detailed Instructions:")
        detailed_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.HTR_detailed_entry = tk.Text(frame, height=20, width=60, wrap=tk.WORD)
        self.HTR_detailed_entry.insert(tk.END, self.HTR_user_prompt)
        self.HTR_detailed_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        # Update the detailed instructions when the text is changed
        self.HTR_detailed_entry.bind("<KeyRelease>", lambda event: setattr(self, 'HTR_user_prompt', self.HTR_user_prompt.get("1.0", tk.END)))

        detailed_scrollbar = tk.Scrollbar(frame, command=self.HTR_detailed_entry.yview)
        detailed_scrollbar.grid(row=3, column=2, sticky="ns")
        self.HTR_detailed_entry.config(yscrollcommand=detailed_scrollbar.set)

        val_label = tk.Label(frame, text=f"Validation Text:")
        val_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.val_label_entry = tk.Text(frame, height=1, width=60)
        self.val_label_entry.insert(tk.END, self.HTR_val_text)
        self.val_label_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.val_label_entry.bind("<KeyRelease>", lambda event: setattr(self, 'HTR_val_text', self.HTR_val_text.get("1.0", tk.END)))
    
        self.HTR_general_entry.bind("<KeyRelease>", lambda event: setattr(self, 'HTR_system_prompt', self.HTR_general_entry.get("1.0", "end-1c")))
        self.HTR_detailed_entry.bind("<KeyRelease>", lambda event: setattr(self, 'HTR_user_prompt', self.HTR_detailed_entry.get("1.0", "end-1c")))
        self.val_label_entry.bind("<KeyRelease>", lambda event: setattr(self, 'HTR_val_text', self.val_label_entry.get("1.0", "end-1c")))

    def show_correct_text_settings(self, frame):
        explanation_label = tk.Label(frame, text=f"""The main function processes each page of text and the corresponding image and by default is used to correct an initially HTRed text.""", wraplength=675, justify=tk.LEFT)
       
        explanation_label.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        model_label = tk.Label(frame, text="Model:")
        model_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.main_model_var = tk.StringVar(value=self.correct_model)
        dropdown = ttk.Combobox(frame, textvariable=self.main_model_var, values=self.model_list, state="readonly", width=30)
        dropdown.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        dropdown.bind("<<ComboboxSelected>>", lambda event: setattr(self, 'correct_text_model', self.main_model_var.get()))

        general_label = tk.Label(frame, text="General Instructions:")
        general_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.main_general_entry = tk.Text(frame, height=5, width=60, wrap=tk.WORD)
        self.main_general_entry.insert(tk.END, self.correct_system_prompt)
        self.main_general_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        self.main_general_entry.bind("<KeyRelease>", lambda event: setattr(self, 'correct_text_system_prompt', self.main_general_entry.get("1.0", tk.END)))

        general_scrollbar = tk.Scrollbar(frame, command=self.main_general_entry.yview)
        general_scrollbar.grid(row=3, column=2, sticky="ns")
        self.main_general_entry.config(yscrollcommand=general_scrollbar.set)

        detailed_label = tk.Label(frame, text="Detailed Instructions:")
        detailed_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.main_detailed_entry = tk.Text(frame, height=20, width=60, wrap=tk.WORD)
        self.main_detailed_entry.insert(tk.END, self.correct_user_prompt)
        self.main_detailed_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.main_detailed_entry.bind("<KeyRelease>", lambda event: setattr(self, 'correct_text_user_prompt', self.main_detailed_entry.get("1.0", tk.END)))

        detailed_scrollbar = tk.Scrollbar(frame, command=self.main_detailed_entry.yview)
        detailed_scrollbar.grid(row=4, column=2, sticky="ns")
        self.main_detailed_entry.config(yscrollcommand=detailed_scrollbar.set)

        val_label = tk.Label(frame, text=f"Validation Text:")
        val_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.val_label_entry = tk.Text(frame, height=1, width=60)
        self.val_label_entry.insert(tk.END, self.correct_val_text)
        self.val_label_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")
        self.val_label_entry.bind("<KeyRelease>", lambda event: setattr(self, 'correct_text_val_text_a', self.val_label_entry.get("1.0", tk.END)))
       
        self.main_general_entry.bind("<KeyRelease>", lambda event: setattr(self, 'correct_system_prompt', self.main_general_entry.get("1.0", "end-1c")))
        self.main_detailed_entry.bind("<KeyRelease>", lambda event: setattr(self, 'correct_user_prompt', self.main_detailed_entry.get("1.0", "end-1c")))
        self.val_label_entry.bind("<KeyRelease>", lambda event: setattr(self, 'correct_val_text', self.val_label_entry.get("1.0", "end-1c")))

    def save_settings(self):
        settings = {
            # HTR Settings
            'HTR_system_prompt': self.HTR_system_prompt,
            'HTR_user_prompt': self.HTR_user_prompt,
            'HTR_val_text': self.HTR_val_text,
            'HTR_model': self.HTR_model,
            
            # Correct Text Settings
            'correct_system_prompt': self.correct_system_prompt,
            'correct_user_prompt': self.correct_user_prompt,
            'correct_val_text': self.correct_val_text,
            'correct_model': self.correct_model,
            
            # API Keys
            'openai_api_key': self.openai_api_key,
            'anthropic_api_key': self.anthropic_api_key,
            'google_api_key': self.google_api_key,
            
            # Model List
            'model_list': self.model_list
        }
        
        try:
            with open(self.settings_file_path, 'w') as f:
                json.dump(settings, f, indent=4)
            
            # Check if settings window exists before showing the message
            if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
                messagebox.showinfo("Success", "Settings saved successfully!", parent=self.settings_window)
            else:
                messagebox.showinfo("Success", "Settings saved successfully!")
                
        except Exception as e:
            if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
                messagebox.showerror("Error", f"Failed to save settings: {e}", parent=self.settings_window)
            else:
                messagebox.showerror("Error", f"Failed to save settings: {e}")

    def load_settings(self):
        try:
            with open(self.settings_file_path, 'r') as f:
                settings = json.load(f)
                
            # HTR Settings
            self.HTR_system_prompt = settings.get('HTR_system_prompt', self.HTR_system_prompt)
            self.HTR_user_prompt = settings.get('HTR_user_prompt', self.HTR_user_prompt)
            self.HTR_val_text = settings.get('HTR_val_text', self.HTR_val_text)
            self.HTR_model = settings.get('HTR_model', self.HTR_model)
            
            # Correct Text Settings
            self.correct_system_prompt = settings.get('correct_system_prompt', self.correct_system_prompt)
            self.correct_user_prompt = settings.get('correct_user_prompt', self.correct_user_prompt)
            self.correct_val_text = settings.get('correct_val_text', self.correct_val_text)
            self.correct_model = settings.get('correct_model', self.correct_model)
            
            # API Keys
            self.openai_api_key = settings.get('openai_api_key', '')
            self.anthropic_api_key = settings.get('anthropic_api_key', '')
            self.google_api_key = settings.get('google_api_key', '')
            
            # Model List
            self.model_list = settings.get('model_list', self.model_list)

            # Update UI if settings window is open
            if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
                self.show_settings("APIs and Login Settings", self.settings_window.winfo_children()[1])
                self.show_settings("HTR Settings", self.settings_window.winfo_children()[1])
                self.show_settings("Correct Text Settings", self.settings_window.winfo_children()[1])
                
        except FileNotFoundError:
            self.restore_defaults()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}")
    
    def restore_defaults(self):
        self.HTR_system_prompt = '''Your task is to accurately transcribe handwritten historical documents, minimizing the CER and WER. Work character by character, word by word, line by line, transcribing the text exactly as it appears on the page. To maintain the authenticity of the historical text, retain spelling errors, grammar, syntax, and punctuation as well as line breaks. Transcribe all the text on the page including headers, footers, marginalia, insertions, page numbers, etc. If these are present, insert them where indicated by the author (as applicable). In your response, write: "Transcription:" followed only by your accurate transcription'''
        
        self.HTR_user_prompt = '''Carefully transcribe this page from an 18th/19th century document. In your response, write: "Transcription:" followed only by your accurate transcription.'''
        
        self.HTR_val_text = "Transcription:"
        self.HTR_model = "gemini-1.5-pro-002"

        self.correct_system_prompt = '''Your task is to compare handwritten pages of text with corresponding draft transcriptions, correcting the transcription to produce an accurate, publishable transcript. Be sure that the spelling, syntax, punctuation, and line breaks in the transcription match those on the handwritten page to preserve the historical integrity of the document. Numbers also easily misread, so pay close attention to digits. You must also ensure that the transcription begins and ends in the same place as the handwritten document. Include any catchwords at the bottom of the page. In your response write "Corrected Transcript:" followed by your corrected transcription.'''
        
        self.correct_user_prompt = '''Your task is to use the handwritten page image to correct the following transcription, retaining the spelling, syntax, punctuation, line breaks, catchwords, etc of the original.\n\n{text_to_process}'''
        
        self.correct_val_text = "Corrected Transcript:"
        self.correct_model = "claude-3-5-sonnet-20240620"

        self.model_list = [
            "gpt-4o",
            "gpt-4o-2024-08-06",
            "gpt-4o-mini",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "gemini-1.5-flash-001",
            "gemini-1.5-flash-002",
            "gemini-1.5-pro-001",
            "gemini-1.5-pro-002"
        ]

        self.openai_api_key = ""
        self.anthropic_api_key = ""
        self.google_api_key = ""
        
    def on_settings_window_close(self, window):
        self.toggle_button_state()
        window.destroy()

# Image and Navigation Functions

    def navigate_images(self, direction):
        self.update_df()

        total_images = len(self.main_df) - 1

        if total_images >= 0:
            if direction == -2:  # Go to the first image
                self.page_counter = 0
            elif direction == -1:  # Go to the previous image
                if self.page_counter > 0:
                    self.page_counter -= 1
            elif direction == 1:  # Go to the next image
                if self.page_counter < total_images:
                    self.page_counter += 1
            elif direction == 2:  # Go to the last image
                self.page_counter = total_images
            elif direction == 0:  # Go to a specific image
                self.page_counter = self.link_nav

            # Update the current image path
            self.current_image_path = self.main_df.loc[self.page_counter, 'Image_Path']

            # Load the new image
            self.load_image(self.current_image_path)

            # Load the text file
            self.load_text()

        self.counter_update()

    def counter_update(self):
        total_images = len(self.main_df) - 1

        if total_images >= 0:
            self.page_counter_var.set(f"{self.page_counter + 1} / {total_images + 1}")
        else:
            self.page_counter_var.set("0 / 0")

    def start_pan(self, event):
        self.image_display.scan_mark(event.x, event.y)

    def pan(self, event):
        self.image_display.scan_dragto(event.x, event.y, gain=1)

    def zoom(self, event):
        scale = 1.5 if event.delta > 0 else 0.6667

        original_width, original_height = self.original_image.size

        new_width = int(original_width * self.current_scale * scale)
        new_height = int(original_height * self.current_scale * scale)

        if new_width < 50 or new_height < 50:
            return

        resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)

        self.photo_image = ImageTk.PhotoImage(resized_image)

        self.image_display.delete("all")
        self.image_display.create_image(0, 0, anchor="nw", image=self.photo_image)

        self.image_display.config(scrollregion=self.image_display.bbox("all"))

        self.current_scale *= scale

    def scroll(self, event):
        self.image_display.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def load_image(self, image_path):
        # Load the image
        self.original_image = Image.open(image_path)
        
        # Apply the current scale to the image
        original_width, original_height = self.original_image.size
        new_width = int(original_width * self.current_scale)
        new_height = int(original_height * self.current_scale)
        self.original_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
        
        self.photo_image = ImageTk.PhotoImage(self.original_image)

        # Update the canvas item
        self.image_display.delete("all")
        self.image_display.create_image(0, 0, anchor="nw", image=self.photo_image)

        # Update the scroll region
        self.image_display.config(scrollregion=self.image_display.bbox("all"))

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')   

    def resize_image(self, image_path, output_path, max_size=1980):
        with Image.open(image_path) as img:
           
            # Get the original image size
            width, height = img.size
            
            # Determine the larger dimension
            larger_dimension = max(width, height)
            
            # Calculate the scaling factor
            scale = max_size / larger_dimension
            
            # Calculate new dimensions
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Resize the image
            img = img.resize((new_width, new_height), Image.LANCZOS)

            img = ImageOps.exif_transpose(img)
            
            # Save the image with high quality
            img.save(output_path, "JPEG", quality=95)
    
    def process_new_images(self, source_paths):
        successful_copies = 0
        for source_path in source_paths:
            new_index = len(self.main_df)
            file_extension = os.path.splitext(source_path)[1].lower()
            new_file_name = f"{new_index+1:04d}_p{new_index+1:03d}{file_extension}"
            dest_path = os.path.join(self.images_directory, new_file_name)
            
            try:
                # Instead of directly copying, resize and save the image
                self.resize_image(source_path, dest_path)                
                text_file_name = f"{new_index+1:04d}_p{new_index+1:03d}.txt"
                text_file_path = os.path.join(self.images_directory, text_file_name)
                with open(text_file_path, "w", encoding='utf-8') as f:
                    f.write("")
                
                new_row = pd.DataFrame({
                    "Index": [new_index],
                    "Page": [f"{new_index+1:04d}_p{new_index+1:03d}"],
                    "Original_Text": [""],
                    "Initial_Draft_Text": [""],
                    "Final_Draft": [""],
                    "Image_Path": [dest_path],
                    "Text_Path": [text_file_path],
                    "Text_Toggle": ["Original Text"]
                })
                self.main_df = pd.concat([self.main_df, new_row], ignore_index=True)
                successful_copies += 1
            except Exception as e:
                print(f"Error processing file {source_path}: {e}")
                messagebox.showerror("Error", f"Failed to process the image {source_path}:\n{e}")

        if successful_copies > 0:
            self.refresh_display()
        else:
            print("No images were successfully processed")
            messagebox.showinfo("Information", "No images were successfully processed")

    def delete_current_image(self):
        if self.main_df.empty:
            messagebox.showinfo("No Images", "No images to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the current image? This action cannot be undone."):
            return

        try:
            current_index = self.page_counter
            
            # Store the path of files to be deleted
            image_to_delete = self.main_df.loc[current_index, 'Image_Path']
            text_to_delete = self.main_df.loc[current_index, 'Text_Path']

            # Remove the row from the DataFrame
            self.main_df = self.main_df.drop(current_index).reset_index(drop=True)

            # Delete the actual files
            try:
                if os.path.exists(image_to_delete):
                    os.remove(image_to_delete)
                if os.path.exists(text_to_delete):
                    os.remove(text_to_delete)
            except Exception as e:
                self.error_logging(f"Error deleting files: {str(e)}")

            # Renumber the remaining entries
            for idx in range(len(self.main_df)):
                # Update Index
                self.main_df.at[idx, 'Index'] = idx
                
                # Create new page number
                new_page = f"{idx+1:04d}_p{idx+1:03d}"
                self.main_df.at[idx, 'Page'] = new_page
                
                # Get old file paths
                old_image_path = self.main_df.loc[idx, 'Image_Path']
                old_text_path = self.main_df.loc[idx, 'Text_Path']
                
                # Create new file paths
                new_image_name = f"{idx+1:04d}_p{idx+1:03d}{os.path.splitext(old_image_path)[1]}"
                new_text_name = f"{idx+1:04d}_p{idx+1:03d}.txt"
                
                new_image_path = os.path.join(os.path.dirname(old_image_path), new_image_name)
                new_text_path = os.path.join(os.path.dirname(old_text_path), new_text_name)
                
                # Rename files
                if os.path.exists(old_image_path):
                    os.rename(old_image_path, new_image_path)
                if os.path.exists(old_text_path):
                    os.rename(old_text_path, new_text_path)
                
                # Update paths in DataFrame
                self.main_df.at[idx, 'Image_Path'] = new_image_path
                self.main_df.at[idx, 'Text_Path'] = new_text_path

            # Adjust page counter if necessary
            if current_index >= len(self.main_df):
                self.page_counter = len(self.main_df) - 1
            
            # Refresh display
            if not self.main_df.empty:
                self.load_image(self.main_df.loc[self.page_counter, 'Image_Path'])
                self.load_text()
            else:
                # Clear displays if no images remain
                self.text_display.delete("1.0", tk.END)
                self.image_display.delete("all")
                self.text_type_label.config(text="None")

            self.counter_update()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while deleting the image: {str(e)}")
            self.error_logging(f"Error in delete_current_image: {str(e)}")

    def rotate_image(self, direction):
        if not hasattr(self, 'original_image') or self.original_image is None:
            messagebox.showwarning("Warning", "No image loaded to rotate.")
            return

        try:
            # Rotate the original image
            if direction == "clockwise":
                self.original_image = self.original_image.rotate(-90, expand=True)  # -90 for clockwise
            else:
                self.original_image = self.original_image.rotate(90, expand=True)   # 90 for counter-clockwise

            # Get the current image path
            current_image_path = self.main_df.loc[self.page_counter, 'Image_Path']

            # Save the rotated image
            self.original_image.save(current_image_path, quality=95)

            # Update the display
            original_width, original_height = self.original_image.size
            new_width = int(original_width * self.current_scale)
            new_height = int(original_height * self.current_scale)
            
            resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(resized_image)

            # Update the canvas
            self.image_display.delete("all")
            self.image_display.create_image(0, 0, anchor="nw", image=self.photo_image)
            self.image_display.config(scrollregion=self.image_display.bbox("all"))

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while rotating the image: {e}")
            self.error_logging(f"Error in rotate_image: {str(e)}")

# File Functions
    
    def reset_application(self):
        # Clear the main DataFrame
        self.main_df = pd.DataFrame(columns=["Index", "Page", "Original_Text", "Initial_Draft_Text", "Final_Draft", "Image_Path", "Text_Path", "Text_Toggle"])
        
        # Reset page counter
        self.page_counter = 0
               
        # Reset flags
        self.save_toggle = False
        self.find_replace_toggle = False
        
        # Clear text displays
        self.text_display.delete("1.0", tk.END)
        
        # Clear image display
        self.image_display.delete("all")
        self.current_image_path = None
        self.original_image = None
        self.photo_image = None
        
        # Reset zoom and pan
        self.current_scale = 1
        
        # Reset counter
        self.counter_update()
        
        # Clear project and image directories
        self.initialize_temp_directory()
                        
        # Clear the find and replace matches DataFrame
        self.find_replace_matches_df = pd.DataFrame(columns=["Index", "Page"])
        
        # Update the display
        self.text_type_label.config(text="None")
        
    def create_new_project(self):
        if not messagebox.askyesno("New Project", "Creating a new project will reset the current application state. This action cannot be undone. Are you sure you want to proceed?"):
            return  # User chose not to proceed
        
        # Reset the application
        self.reset_application()

        # Enable drag and drop
        self.enable_drag_and_drop()

    def save_project(self):
        if not hasattr(self, 'project_directory') or not self.project_directory:
            # If there's no current project, call save_project_as instead
            self.save_project_as()
            return

        try:
            # Get the project name from the directory path
            project_name = os.path.basename(self.project_directory)
            pbf_file = os.path.join(self.project_directory, f"{project_name}.pbf")

            # Ensure text columns are of type 'object' (string)
            text_columns = ['Original_Text', 'Initial_Draft_Text', 'Final_Draft','Text_Toggle']
            for col in text_columns:
                if col in self.main_df.columns:
                    self.main_df[col] = self.main_df[col].astype('object')

            # Update text files with current content
            for index, row in self.main_df.iterrows():
                text_path = row['Text_Path']
                
                # Determine which text to save based on the Text_Toggle
                if row['Text_Toggle'] == 'Final Draft':
                    text_content = row['Final_Draft']
                elif row['Text_Toggle'] == 'Initial Draft':
                    text_content = row['Initial_Draft_Text']
                else:
                    text_content = row['Original_Text']

                # Write the current text content to the file
                with open(text_path, 'w', encoding='utf-8') as text_file:
                    text_file.write(text_content)

            # Save the DataFrame to the PBF file
            self.main_df.to_csv(pbf_file, index=False, encoding='utf-8')

            messagebox.showinfo("Success", f"Project saved successfully to {self.project_directory}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {e}")
            self.error_logging(f"Failed to save project: {e}")

    def open_project(self):
        project_directory = filedialog.askdirectory(title="Select Project Directory")
        if not project_directory:
            return

        project_name = os.path.basename(project_directory)
        pbf_file = os.path.join(project_directory, f"{project_name}.pbf")
        images_directory = os.path.join(project_directory, "images")

        if not os.path.exists(pbf_file) or not os.path.exists(images_directory):
            messagebox.showerror("Error", "Invalid project directory. Missing PBF file or images directory.")
            return

        try:
            # Read the PBF file
            self.main_df = pd.read_csv(pbf_file, encoding='utf-8')
            
            # Ensure text columns are of type 'object' (string)
            text_columns = ['Original_Text', 'Initial_Draft_Text', 'Final_Draft', 'Text_Toggle']
            for col in text_columns:
                if col in self.main_df.columns:
                    self.main_df[col] = self.main_df[col].astype('object')
            
            # Update the project directory
            self.project_directory = project_directory
            self.images_directory = images_directory
            
            # Reset the page counter and load the first image/text
            self.page_counter = 0
            self.load_image(self.main_df.loc[0, 'Image_Path'])
            self.load_text()
            self.counter_update()
            
            messagebox.showinfo("Success", "Project loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open project: {e}")
            self.error_logging("Failed to open project", str(e))

    def save_project_as(self):
        # Ask the user to select a parent directory for the project
        parent_directory = filedialog.askdirectory(
            title="Select Directory for New Project"
        )
        if not parent_directory:
            return  # User cancelled the operation

        # Prompt the user for a project name
        project_name = simpledialog.askstring("Project Name", "Enter a name for the new project:")
        if not project_name:
            return  # User cancelled or didn't enter a name

        # Create the full path for the new project directory
        project_directory = os.path.join(parent_directory, project_name)

        # Check if the project directory already exists
        if os.path.exists(project_directory):
            if not messagebox.askyesno("Directory Exists", "A directory with this name already exists. Do you want to use it anyway?"):
                return  # User chose not to use the existing directory

        try:
            # Create the project directory and images subdirectory
            os.makedirs(project_directory, exist_ok=True)
            images_directory = os.path.join(project_directory, "images")
            os.makedirs(images_directory, exist_ok=True)

            # Create the PBF file path
            pbf_file = os.path.join(project_directory, f"{project_name}.pbf")

            # Ensure text columns are of type 'object' (string)
            text_columns = ['Original_Text', 'Initial_Draft_Text', 'Final_Draft', 'Text_Toggle']
            for col in text_columns:
                if col in self.main_df.columns:
                    self.main_df[col] = self.main_df[col].astype('object')

            # Copy images and create/copy text files
            for index, row in self.main_df.iterrows():
                # Handle image file
                old_image_path = row['Image_Path']
                new_image_filename = os.path.basename(old_image_path)
                new_image_path = os.path.join(images_directory, new_image_filename)
                self.resize_image(old_image_path, new_image_path)
                
                # Update the image path in the DataFrame
                self.main_df.at[index, 'Image_Path'] = new_image_path

                # Handle text file
                text_filename = os.path.splitext(new_image_filename)[0] + '.txt'
                new_text_path = os.path.join(images_directory, text_filename)
                
                # Check if there's existing text content
                text_content = row.get('Original_Text', '')
                if not text_content:
                    text_content = row.get('Initial_Draft_Text', '')
                if not text_content:
                    text_content = row.get('Final_Draft', '')

                # Write the text content (or create an empty file if no content)
                with open(new_text_path, 'w', encoding='utf-8') as text_file:
                    text_file.write(text_content)

                # Update the text path in the DataFrame
                self.main_df.at[index, 'Text_Path'] = new_text_path

                # Ensure all text fields have at least an empty string
                for col in ['Original_Text', 'Initial_Draft_Text', 'Final_Draft']:
                    if col not in self.main_df.columns or pd.isna(self.main_df.at[index, col]):
                        self.main_df.at[index, col] = ''

                # Ensure Text_Toggle is set
                if 'Text_Toggle' not in self.main_df.columns or pd.isna(self.main_df.at[index, 'Text_Toggle']):
                    self.main_df.at[index, 'Text_Toggle'] = 'Original Text'

            # Save the DataFrame to the PBF file
            self.main_df.to_csv(pbf_file, index=False, encoding='utf-8')

            messagebox.showinfo("Success", f"Project saved successfully to {project_directory}")
            
            # Update the project directory
            self.project_directory = project_directory
            self.images_directory = images_directory
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {e}")
            self.error_logging(f"Failed to save project: {e}")        # Ask the user to select a parent directory for the project
            parent_directory = filedialog.askdirectory(
                title="Select Directory for New Project"
            )
            if not parent_directory:
                return  # User cancelled the operation

            # Prompt the user for a project name
            project_name = simpledialog.askstring("Project Name", "Enter a name for the new project:")
            if not project_name:
                return  # User cancelled or didn't enter a name

            # Create the full path for the new project directory
            project_directory = os.path.join(parent_directory, project_name)

            # Check if the project directory already exists
            if os.path.exists(project_directory):
                if not messagebox.askyesno("Directory Exists", "A directory with this name already exists. Do you want to use it anyway?"):
                    return  # User chose not to use the existing directory

            try:
                # Create the project directory and images subdirectory
                os.makedirs(project_directory, exist_ok=True)
                images_directory = os.path.join(project_directory, "images")
                os.makedirs(images_directory, exist_ok=True)

                # Create the PBF file path
                pbf_file = os.path.join(project_directory, f"{project_name}.pbf")

                # Copy images and create/copy text files
                for index, row in self.main_df.iterrows():
                    # Handle image file
                    old_image_path = row['Image_Path']
                    new_image_filename = os.path.basename(old_image_path)
                    new_image_path = os.path.join(images_directory, new_image_filename)
                    shutil.copy2(old_image_path, new_image_path)
                    
                    # Update the image path in the DataFrame
                    self.main_df.at[index, 'Image_Path'] = new_image_path

                    # Handle text file
                    text_filename = os.path.splitext(new_image_filename)[0] + '.txt'
                    new_text_path = os.path.join(images_directory, text_filename)
                    
                    # Check if there's existing text content
                    text_content = row.get('Original_Text', '')
                    if not text_content:
                        text_content = row.get('Initial_Draft_Text', '')
                    if not text_content:
                        text_content = row.get('Final_Draft', '')

                    # Write the text content (or create an empty file if no content)
                    with open(new_text_path, 'w', encoding='utf-8') as text_file:
                        text_file.write(text_content)

                    # Update the text path in the DataFrame
                    self.main_df.at[index, 'Text_Path'] = new_text_path

                    # Ensure all text fields have at least an empty string
                    if 'Original_Text' not in self.main_df.columns or pd.isna(self.main_df.at[index, 'Original_Text']):
                        self.main_df.at[index, 'Original_Text'] = ''
                    if 'Initial_Draft_Text' not in self.main_df.columns or pd.isna(self.main_df.at[index, 'Initial_Draft_Text']):
                        self.main_df.at[index, 'Initial_Draft_Text'] = ''
                    if 'Final_Draft' not in self.main_df.columns or pd.isna(self.main_df.at[index, 'Final_Draft']):
                        self.main_df.at[index, 'Final_Draft'] = ''

                    # Ensure Text_Toggle is set
                    if 'Text_Toggle' not in self.main_df.columns or pd.isna(self.main_df.at[index, 'Text_Toggle']):
                        self.main_df.at[index, 'Text_Toggle'] = 'Original Text'

                # Save the DataFrame to the PBF file
                self.main_df.to_csv(pbf_file, index=False, encoding='utf-8')

                messagebox.showinfo("Success", f"Project saved successfully to {project_directory}")
                
                # Update the project directory
                self.project_directory = project_directory
                self.images_directory = images_directory
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save project: {e}")
                self.error_logging(f"Failed to save project: {e}")

    def open_pdf(self, pdf_file=None):
        if pdf_file is None:
            pdf_file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not pdf_file:
            return

        progress_window, progress_bar, progress_label = self.create_progress_window("Processing PDF...")

        try:
            pdf_document = fitz.open(pdf_file)
            total_pages = len(pdf_document)
            self.reset_application()

            for page_num in range(total_pages):
                self.update_progress(progress_bar, progress_label, page_num + 1, total_pages)

                page = pdf_document[page_num]

                # Extract image at a lower resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                temp_image_path = os.path.join(self.temp_directory, f"temp_page_{page_num + 1}.jpg")
                pix.save(temp_image_path)

                # Resize and save the image using the existing resize_image method
                image_filename = f"{page_num + 1:04d}_p{page_num + 1:03d}.jpg"
                image_path = os.path.join(self.images_directory, image_filename)
                self.resize_image(temp_image_path, image_path)

                # Remove the temporary image
                os.remove(temp_image_path)

                # Extract text
                text_content = page.get_text()
                text_filename = f"{page_num + 1:04d}_p{page_num + 1:03d}.txt"
                text_path = os.path.join(self.images_directory, text_filename)
                with open(text_path, "w", encoding='utf-8') as text_file:
                    text_file.write(text_content)

                # Add to DataFrame
                new_row = pd.DataFrame({
                    "Index": [page_num],
                    "Page": [f"{page_num + 1:04d}_p{page_num + 1:03d}"],
                    "Original_Text": [text_content],
                    "Initial_Draft_Text": [""],
                    "Final_Draft": [""],
                    "Image_Path": [image_path],
                    "Text_Path": [text_path],
                    "Text_Toggle": ["Original Text"]
                })
                self.main_df = pd.concat([self.main_df, new_row], ignore_index=True)

            pdf_document.close()
            self.refresh_display()
            self.close_progress_window(progress_window)
            messagebox.showinfo("Success", f"PDF processed successfully. {total_pages} pages extracted.")

        except Exception as e:
            self.close_progress_window(progress_window)
            messagebox.showerror("Error", f"An error occurred while processing the PDF: {str(e)}")
            self.error_logging(f"Error in open_pdf: {str(e)}")

        finally:
            self.enable_drag_and_drop()

 # Utility Functions   

    def copy(self):
        self.text_display.event_generate("<<Copy>>")   
    
    def cut(self):
        self.text_display.event_generate("<<Cut>>")
    
    def paste(self):
        self.text_display.event_generate("<<Paste>>")
    
    def undo(self, event):
        try:
            self.text_display.edit_undo()
        except tk.TclError:
            pass
    
    def redo(self, event):
        try:
            self.text_display.edit_redo()
        except tk.TclError:
            pass

    def find_right_text(self, index_no):
        original_text = self.main_df.loc[index_no, 'Original_Text'] if 'Original_Text' in self.main_df.columns else ""
        initial_draft_text = self.main_df.loc[index_no, 'Initial_Draft_Text'] if 'Initial_Draft_Text' in self.main_df.columns else ""
        final_draft_text = self.main_df.loc[index_no, 'Final_Draft'] if 'Final_Draft' in self.main_df.columns else ""

        if pd.notna(final_draft_text) and self.main_df.loc[index_no, 'Text_Toggle'] == "Final Draft":
            text = final_draft_text
            self.text_type_label.config(text="Final Draft")
        elif pd.notna(initial_draft_text) and self.main_df.loc[index_no, 'Text_Toggle'] == "Initial Draft":
            text = initial_draft_text
            self.text_type_label.config(text="Initial Draft")
        elif pd.notna(original_text) and self.main_df.loc[index_no, 'Text_Toggle'] == "Original Text":
            text = original_text
            self.text_type_label.config(text="Original Text")
        else:
            text = ""
            self.text_type_label.config(text="No Text")

        return text
    
    def toggle_button_state(self):
                
        if self.button1['state'] == "normal" and self.button2['state'] == "normal" and self.button4['state'] == "normal" and self.button5['state'] == "normal":
            self.button1.config(state="disabled")
            self.button2.config(state="disabled")
            self.button4.config(state="disabled")
            self.button5.config(state="disabled")

        else:
            self.button1.config(state="normal")
            self.button2.config(state="normal")
            self.button4.config(state="normal")
            self.button5.config(state="normal")

    def get_active_category(self, row_index):
        if self.main_df.loc[row_index, 'Text_Toggle'] == "Original Text":
            active_category = "Original_Text"
        elif self.main_df.loc[row_index, 'Text_Toggle'] == "Initial Draft":
            active_category = "Initial_Draft_Text"
        elif self.main_df.loc[row_index, 'Text_Toggle'] == "Final Draft":
            active_category = "Final_Draft"
        else:
            active_category = "Original_Text"
        return active_category

    def format_pages(self, text):
        # Delete all newline characters
        text = text.replace("\n", " ")
        
        # Add a space after each colon
        text = text.replace(":", ": ")
        
        # Find any dates followed by a day of the week without a colon and insert a colon after the date
        text = re.sub(r"(\d{4}-\d{2}-\d{2}) (Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day([^:])", r"\1 \2day: \3", text)
        
        # Find any dates followed by a day of the week and a colon, and insert two new line characters before the date
        text = re.sub(r"(\d{4}-\d{2}-\d{2}) (Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day:", r"\n\n\1 \2day:", text)
        
        # Find any lines that end with a date followed by a day of the week and "to", and replace the newline characters that follow with a space
        text = re.sub(r"(\d{4}-\d{2}-\d{2}) (Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day to \n\n", r"\1 \2day to ", text)
        
        # Find any double spaces and replace them with a single space
        text = re.sub(r"  ", " ", text)
        
        # Remove ellipses and ** to ***** characters
        text = re.sub(r"\.{3}|\*{2,5}|'{2,3}|`{2,5}", "", text) 
        return text

    def error_logging(self, error_message, additional_info=None):
        try:
            error_logs_path = "util/error_logs.txt" 
            with open(error_logs_path, "a", encoding='utf-8') as file:
                log_message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {error_message}"
                if additional_info:
                    log_message += f" - Additional Info: {additional_info}"
                file.write(log_message + "\n")
        except Exception as e:
            print(f"Error logging failed: {e}")
    
    def drop(self, event):
        file_paths = event.data
        
        # Split the input string by spaces, but keep content within curly braces together
        file_paths = re.findall(r'\{[^}]*\}|\S+', file_paths)
        
        valid_images = []
        pdf_files = []
        invalid_files = []

        for file_path in file_paths:
            # Remove curly braces and any quotation marks
            file_path = file_path.strip('{}').strip('"')
            
            if os.path.isfile(file_path):
                lower_path = file_path.lower()
                if lower_path.endswith(('.jpg', '.jpeg')):
                    valid_images.append(file_path)
                elif lower_path.endswith('.png'):
                    # Convert PNG to JPEG
                    try:
                        img = Image.open(file_path)
                        if img.mode in ('RGBA', 'LA'):
                            # Remove alpha channel
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[-1])
                            img = background
                        # Create temporary JPEG file
                        jpeg_path = os.path.splitext(file_path)[0] + '_converted.jpg'
                        img.convert('RGB').save(jpeg_path, 'JPEG', quality=95)
                        valid_images.append(jpeg_path)
                    except Exception as e:
                        print(f"Error converting PNG file {file_path}: {e}")
                        invalid_files.append(file_path)
                elif lower_path.endswith('.pdf'):
                    pdf_files.append(file_path)
                else:
                    invalid_files.append(file_path)
            else:
                invalid_files.append(file_path)

        # Process valid image files
        if valid_images:
            self.process_new_images(valid_images)
            
            # Clean up temporary converted files
            for image_path in valid_images:
                if image_path.endswith('_converted.jpg'):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        print(f"Error removing temporary file {image_path}: {e}")

        # Process PDF files
        if pdf_files:
            for pdf_file in pdf_files:
                try:
                    self.open_pdf(pdf_file)
                except Exception as e:
                    print(f"Error processing PDF file {pdf_file}: {e}")
                    messagebox.showerror("Error", f"Failed to process PDF file {pdf_file}: {e}")
        
        # Report invalid files
        if invalid_files:
            invalid_files_str = "\n".join(invalid_files)
            print(f"Invalid files: {invalid_files_str}")
            messagebox.showwarning("Invalid Files", 
                f"The following files were not processed because they are not valid image or PDF files:\n\n{invalid_files_str}")
                            
    def refresh_display(self):
        if not self.main_df.empty:
            self.page_counter = len(self.main_df) - 1
            self.load_image(self.main_df.iloc[-1]['Image_Path'])
            self.load_text()
            self.counter_update()
        else:
            print("No images to display")
            # Clear the image display or show a placeholder image
            self.image_display.delete("all")
            # Clear the text display
            self.text_display.delete("1.0", tk.END)
            self.counter_update()
    
    def enable_drag_and_drop(self):
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.drop)
    
# Loading Functions

    def open_folder(self, toggle):
        directory = filedialog.askdirectory()
        if directory:
            self.directory_path = directory  # Set the directory_path attribute
            self.project_directory = directory
            self.images_directory = os.path.join(self.project_directory, "images")
            os.makedirs(self.images_directory, exist_ok=True)

            # Reset application
            self.reset_application()

            if toggle == "Images without Text":
                self.load_files_from_folder_no_text()
            else:
                self.load_files_from_folder()
            self.enable_drag_and_drop()

    def load_files_from_folder(self):
        if not self.directory_path:
            messagebox.showerror("Error", "No directory selected.")
            return

        # Reset DataFrames
        self.main_df = pd.DataFrame(columns=["Index", "Page", "Original_Text", "Initial_Draft_Text", "Final_Draft", "Image_Path", "Text_Path", "Text_Toggle"])

        # Reset page counter
        self.page_counter = 0

        # Create backup directory
        backup_directory = os.path.join(self.directory_path, "bkup")
        os.makedirs(backup_directory, exist_ok=True)

        # Get image and text files
        image_files = [f for f in os.listdir(self.directory_path) if f.lower().endswith((".jpg", ".jpeg"))]
        text_files = [f for f in os.listdir(self.directory_path) if f.lower().endswith(".txt")]

        if not image_files:
            messagebox.showinfo("No Files", "No image files found in the selected directory.")
            return

        # Sort files based on the numeric prefix
        def sort_key(filename):
            match = re.match(r'(\d+)', filename)
            return int(match.group(1)) if match else float('inf')

        image_files.sort(key=sort_key)
        text_files.sort(key=sort_key)

        # Check if the number of image and text files match
        if len(image_files) != len(text_files):
            messagebox.showerror("Error", "The number of image files and text files does not match.")
            return

        # Populate the DataFrame
        for i, (image_file, text_file) in enumerate(zip(image_files, text_files), start=1):
            image_path = os.path.join(self.directory_path, image_file)
            text_path = os.path.join(self.directory_path, text_file)

            # Create backup image file with resizing
            backup_image_path = os.path.join(backup_directory, f"{os.path.splitext(image_file)[0]}.jpg")
            self.resize_image(image_path, backup_image_path)

            # Create backup text file
            backup_text_path = os.path.join(backup_directory, text_file)
            shutil.copy2(text_path, backup_text_path)

            # Read text content
            with open(text_path, "r", encoding='utf-8') as f:
                text_content = f.read()

            page = f"{i:04d}_p{i:03d}"  # Format the page number
            self.main_df.loc[i-1] = [i-1, page, text_content, "", "", "", image_path, text_path, "Original Text"]

        # Load the first image and text file
        if len(self.main_df) > 0:
            self.current_image_path = self.main_df.loc[0, 'Image_Path']
            self.load_image(self.current_image_path)
            self.load_text()
        else:
            messagebox.showinfo("No Files", "No files found in the selected directory.")

        self.counter_update()

    def load_files_from_folder_no_text(self):
        if self.directory_path:
            self.people_and_places_flag = False
            # Initialize main_df with all required columns
            self.main_df = pd.DataFrame(columns=[
                "Index", 
                "Page", 
                "Original_Text", 
                "Initial_Draft_Text", 
                "Final_Draft", 
                "Image_Path", 
                "Text_Path", 
                "Text_Toggle"
            ])

            # Reset the page counter and flags
            self.page_counter = 0

            # Create a backup directory
            backup_directory = os.path.join(self.directory_path, "bkup")
            os.makedirs(backup_directory, exist_ok=True)

            # Load image files
            image_files = [file for file in os.listdir(self.directory_path) 
                        if file.lower().endswith((".jpg", ".jpeg"))]

            if not image_files:
                messagebox.showinfo("No Files", "No image files found in the selected directory.")
                return

            # Sort image files based on the numeric part after the underscore
            image_files.sort(key=lambda x: int(x.split("_")[0]) if "_" in x else float('inf'))

            # Populate the DataFrame
            for i, image_file in enumerate(image_files, start=1):
                image_path = os.path.join(self.directory_path, image_file)

                # Create backup image file with resizing
                backup_image_path = os.path.join(backup_directory, f"{os.path.splitext(image_file)[0]}.jpg")
                self.resize_image(image_path, backup_image_path)

                # Create a blank text file with the same name as the image file
                text_path = os.path.join(self.directory_path, os.path.splitext(image_file)[0] + ".txt")
                with open(text_path, "w", encoding='utf-8') as f:
                    f.write("")

                page = f"{i:04d}_p{i:03d}"  # Format the page number
                
                # Create new row as a dictionary
                new_row = {
                    "Index": i-1,
                    "Page": page,
                    "Original_Text": "",
                    "Initial_Draft_Text": "",
                    "Final_Draft": "",
                    "Image_Path": image_path,
                    "Text_Path": text_path,
                    "Text_Toggle": "Original Text"
                }
                
                # Add the new row to the DataFrame
                self.main_df.loc[i-1] = new_row

            # Load the first image and text file
            if len(self.main_df) > 0:
                self.current_image_path = self.main_df.loc[0, 'Image_Path']
                self.load_image(self.current_image_path)
                self.load_text()
            else:
                messagebox.showinfo("No Files", "No files found in the selected directory.")

            self.counter_update()  
             
    def load_text(self):
        index = self.page_counter

        text = self.find_right_text(index)

        # Set the text of the Text widget
        self.text_display.delete("1.0", tk.END)
        if text:  # Only insert text if it's not empty
            self.text_display.insert("1.0", text)

        if self.find_replace_toggle:
            self.highlight_text()

        self.counter_update()

    def update_df(self):
        self.save_toggle = False
        # Get the text from the Text widget
        text = self.text_display.get("1.0", tk.END)

        index = self.page_counter

        if pd.notna(self.main_df.loc[index, 'Final_Draft']) and self.main_df.loc[index, 'Text_Toggle'] == "Final Draft":
            self.main_df.loc[index, 'Final_Draft'] = text
        elif pd.notna(self.main_df.loc[index, 'Initial_Draft_Text']) and self.main_df.loc[index, 'Text_Toggle'] == "Initial Draft":
            self.main_df.loc[index, 'Initial_Draft_Text'] = text
        elif pd.notna(self.main_df.loc[index, 'Original_Text']) and self.main_df.loc[index, 'Text_Toggle'] == "Original Text":
            self.main_df.loc[index, 'Original_Text'] = text
        else:
            pass

    def edit_single_image(self):
        if self.main_df.empty:
            messagebox.showerror("Error", "No images have been loaded. Please load some images first.")
            return

        # Hide the main window
        self.withdraw()

        # Create a temporary directory for the single image
        single_temp_dir = os.path.join(self.images_directory, "single_temp")
        os.makedirs(single_temp_dir, exist_ok=True)

        try:
            # Copy the current image to temp directory
            current_image_path = self.main_df.loc[self.page_counter, 'Image_Path']
            temp_image_name = os.path.basename(current_image_path)
            temp_image_path = os.path.join(single_temp_dir, temp_image_name)
            
            shutil.copy2(current_image_path, temp_image_path)

            # Create an instance of ImageSplitter with the temp directory
            image_splitter = ImageSplitter(single_temp_dir)
            
            # Wait for the ImageSplitter window to close
            self.wait_window(image_splitter)

            if image_splitter.status == "saved":
                self.process_edited_single_image(current_image_path)
            elif image_splitter.status == "discarded":
                pass

        except Exception as e:
            print(f"Error in edit_single_image: {str(e)}")
            messagebox.showerror("Error", f"An error occurred while editing the image: {str(e)}")

        finally:
            # Clean up
            if os.path.exists(single_temp_dir):
                shutil.rmtree(single_temp_dir, ignore_errors=True)
            
            # Show the main window again
            self.deiconify()

    def process_edited_single_image(self, original_image_path):
        pass_images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "util", "subs", "pass_images")

        if not os.path.exists(pass_images_dir):
            messagebox.showerror("Error", f"pass_images directory not found at: {pass_images_dir}")
            return

        try:
            # Get all edited images from pass_images directory
            edited_images = sorted([f for f in os.listdir(pass_images_dir) if f.endswith(('.jpg', '.jpeg'))])
            
            if edited_images:
                current_index = self.page_counter
                
                # Make a backup of the original image
                backup_path = original_image_path + '.bak'
                shutil.copy2(original_image_path, backup_path)

                if len(edited_images) == 1:
                    # Single image case - just replace the original
                    edited_image_path = os.path.join(pass_images_dir, edited_images[0])
                    shutil.copy2(edited_image_path, original_image_path)
                    
                else:
                    # Multiple images case
                    # First, shift all existing entries after the current index
                    shift_amount = len(edited_images) - 1
                    
                    # Create a copy of the DataFrame for modification
                    new_df = self.main_df.copy()
                    
                    # Shift existing entries
                    for idx in range(len(self.main_df) - 1, current_index, -1):
                        old_index = idx
                        new_index = idx + shift_amount
                        
                        # Update the Index
                        new_df.loc[new_index] = self.main_df.loc[old_index].copy()
                        
                        # Update the Page number
                        new_page = f"{new_index+1:04d}_p{new_index+1:03d}"
                        new_df.at[new_index, 'Page'] = new_page
                        
                        # Update file paths
                        old_image_path = self.main_df.loc[old_index, 'Image_Path']
                        old_text_path = self.main_df.loc[old_index, 'Text_Path']
                        
                        new_image_name = f"{new_index+1:04d}_p{new_index+1:03d}.jpg"
                        new_text_name = f"{new_index+1:04d}_p{new_index+1:03d}.txt"
                        
                        new_image_path = os.path.join(os.path.dirname(old_image_path), new_image_name)
                        new_text_path = os.path.join(os.path.dirname(old_text_path), new_text_name)
                        
                        # Rename files
                        if os.path.exists(old_image_path):
                            shutil.move(old_image_path, new_image_path)
                        if os.path.exists(old_text_path):
                            shutil.move(old_text_path, new_text_path)
                        
                        new_df.at[new_index, 'Image_Path'] = new_image_path
                        new_df.at[new_index, 'Text_Path'] = new_text_path

                    # Insert new entries for the split images
                    for i, img_file in enumerate(edited_images):
                        new_index = current_index + i
                        new_page = f"{new_index+1:04d}_p{new_index+1:03d}"
                        
                        # Create paths for new files
                        new_image_name = f"{new_index+1:04d}_p{new_index+1:03d}.jpg"
                        new_text_name = f"{new_index+1:04d}_p{new_index+1:03d}.txt"
                        
                        new_image_path = os.path.join(os.path.dirname(original_image_path), new_image_name)
                        new_text_path = os.path.join(os.path.dirname(original_image_path), new_text_name)
                        
                        # Copy the edited image
                        edited_image_path = os.path.join(pass_images_dir, img_file)
                        shutil.copy2(edited_image_path, new_image_path)
                        
                        # Create blank text file
                        with open(new_text_path, 'w', encoding='utf-8') as f:
                            f.write("")
                        
                        # Create new row
                        new_row = {
                            "Index": new_index,
                            "Page": new_page,
                            "Original_Text": "",
                            "Initial_Draft_Text": "",
                            "Final_Draft": "",
                            "Image_Path": new_image_path,
                            "Text_Path": new_text_path,
                            "Text_Toggle": "Original Text"
                        }
                        
                        new_df.loc[new_index] = new_row

                    # Update the main DataFrame
                    self.main_df = new_df.sort_index()

                # Clear the pass_images directory
                for filename in os.listdir(pass_images_dir):
                    file_path = os.path.join(pass_images_dir, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)

                # Reload the display
                self.refresh_display()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while processing edited image: {str(e)}")
            self.error_logging(f"Error in process_edited_single_image: {str(e)}")

    def edit_all_images(self):
        if self.main_df.empty:
            messagebox.showerror("Error", "No images have been loaded. Please load some images first.")
            return

        # Show warning message
        if not messagebox.askyesno("Warning", 
                                "This action will replace all current images and text with the edited versions. "
                                "All existing text will be lost. This action cannot be undone. "
                                "Do you want to continue?"):
            return

        # Hide the main window
        self.withdraw()

        # Create a temporary directory for all images
        all_temp_dir = os.path.join(self.images_directory, "all_temp")
        os.makedirs(all_temp_dir, exist_ok=True)

        try:
            # Copy all images to temp directory
            for index, row in self.main_df.iterrows():
                current_image_path = row['Image_Path']
                temp_image_name = os.path.basename(current_image_path)
                temp_image_path = os.path.join(all_temp_dir, temp_image_name)
                shutil.copy2(current_image_path, temp_image_path)

            # Create an instance of ImageSplitter with the temp directory
            image_splitter = ImageSplitter(all_temp_dir)
            
            # Wait for the ImageSplitter window to close
            self.wait_window(image_splitter)

            if image_splitter.status == "saved":
                # Reset the application state
                self.reset_application()
                
                # Get the pass_images directory path
                pass_images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                            "util", "subs", "pass_images")

                if not os.path.exists(pass_images_dir):
                    messagebox.showerror("Error", f"pass_images directory not found at: {pass_images_dir}")
                    return

                # Set the directory path to pass_images and load the files
                self.directory_path = pass_images_dir
                self.load_files_from_folder_no_text()


            elif image_splitter.status == "discarded":
                messagebox.showinfo("Cancelled", "Image editing was cancelled. No changes were made.")

        except Exception as e:
            print(f"Error in edit_all_images: {str(e)}")
            messagebox.showerror("Error", f"An error occurred while editing the images: {str(e)}")
            self.error_logging(f"Error in edit_all_images: {str(e)}")

        finally:
            # Clean up
            if os.path.exists(all_temp_dir):
                shutil.rmtree(all_temp_dir, ignore_errors=True)
            
            # Show the main window again
            self.deiconify()

# Functions for Buttons
    
    def revert_current_page(self):
        index = self.page_counter
        
        if tk.messagebox.askyesno("Revert to Original", "Are you sure you want to revert the current page to the original text? This action cannot be undone."):
            self.main_df.loc[index, 'Final_Draft'] = ""
            self.main_df.loc[index, 'Initial_Draft_Text'] = ""
            self.main_df.loc[index, 'Text_Toggle'] = "Original Text"

            self.load_text()

    def revert_all_pages(self):
        self.main_df['Final_Draft'] = ""
        self.main_df['Initial_Draft_Text'] = ""
        self.main_df['Text_Toggle'] = "Original Text"

        self.page_counter = 0

        self.load_text()
        self.counter_update()         
                        
    def export(self, export_path):
        self.toggle_button_state()        
        combined_text = ""
        
        # Combine all the processed_text values into a single string
        for index, row in self.main_df.iterrows():
            text = self.find_right_text(index)

            if text[0].isalpha():
                combined_text += text
            else:
                combined_text += "\n\n" + text
        
        # Delete instances of three or more newline characters in a row, replacing them with two newline characters
        combined_text = re.sub(r"\n{3,}", "\n\n", combined_text)

        if not export_path:  # User cancelled the file dialog
            self.toggle_button_state()
            return

        # Save the combined text to the chosen file
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(combined_text)
        
        self.toggle_button_state()
    
    def manual_export(self):
        self.toggle_button_state()        
        combined_text = ""

        # Use a file dialog to ask the user where to save the exported text
        export_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save Exported Text As"
        )
        
        # Combine all the processed_text values into a single string
        for index, row in self.main_df.iterrows():
            text = self.find_right_text(index)

            if text[0].isalpha():
                combined_text += text
            else:
                combined_text += "\n\n" + text
        
        # Delete instances of three or more newline characters in a row, replacing them with two newline characters
        combined_text = re.sub(r"\n{3,}", "\n\n", combined_text)

        if not export_path:  # User cancelled the file dialog
            self.toggle_button_state()
            return

        # Save the combined text to the chosen file
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(combined_text)

        self.toggle_button_state()

# Routing and Variables Functions
    
    async def run_send_to_claude_api(self, system_prompt, user_prompt, temp, image_base64, text_to_process, val_text, engine, index, format_function=False, api_timeout=120):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            response, index = await self.send_to_claude_api_in_parallel(system_prompt, user_prompt, temp, image_base64, text_to_process, val_text, engine, index, format_function, api_timeout)
        finally:
            loop.close()      
        
        return response, index
    
# Progress Bar Functions

    def create_progress_window(self, title):
        # Create a new Tkinter window for the progress bar
        progress_window = tk.Toplevel(self.master)
        progress_window.title(title)
        progress_window.geometry("400x100")

        # Create a progress bar
        progress_bar = ttk.Progressbar(progress_window, length=350, mode='determinate')
        progress_bar.pack(pady=20)

        # Create a label to display the progress percentage
        progress_label = tk.Label(progress_window, text="0%")
        progress_label.pack()

        # Ensure the progress window is displayed on top of the main window
        progress_window.attributes("-topmost", True)

        return progress_window, progress_bar, progress_label

    def update_progress(self, progress_bar, progress_label, processed_rows, total_rows):
        # Calculate the progress percentage
        if total_rows > 0:
            progress = (processed_rows / total_rows) * 100
            progress_bar['value'] = progress
            progress_label.config(text=f"{progress:.2f}%")
        
        # Update the progress bar and label
        progress_bar.update()
        progress_label.update()
    
    def close_progress_window(self, progress_window):
        # Close the progress window
        progress_window.destroy()

# Find and Replace Functions

    def find_and_replace(self, event=None):
        try:
            selected_text = ""
            original_text = None
            start_index = None
            end_index = None

            # Check if any text is selected in the text_display
            if self.text_display.tag_ranges("sel"):
                selected_text = self.text_display.get("sel.first", "sel.last")
                original_text = self.text_display.get("1.0", tk.END)
                start_index = self.text_display.index("sel.first")
                end_index = self.text_display.index("sel.last")

            selected_text = selected_text.strip().strip(string.punctuation)

            # If the find and replace window is already open, update the search entry
            if self.find_replace_toggle:
                self.search_entry.delete(0, tk.END)
                self.search_entry.insert(0, selected_text)
                return

            # Create the Find and Replace window
            self.find_replace_window = tk.Toplevel(self)
            self.find_replace_window.title("Find and Replace")
            self.find_replace_window.attributes("-topmost", True)  # Keep the window always on top
            self.find_replace_window.geometry("400x200")  # Set the window size

            search_label = tk.Label(self.find_replace_window, text="Search:")
            search_label.grid(row=0, column=0, padx=5, pady=5)
            self.search_entry = tk.Entry(self.find_replace_window, width=50)
            self.search_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=5)
            self.search_entry.insert(0, selected_text)  # Use the selected text as the default search term

            replace_label = tk.Label(self.find_replace_window, text="Replace:")
            replace_label.grid(row=1, column=0, padx=5, pady=5)
            self.replace_entry = tk.Entry(self.find_replace_window, width=50)
            self.replace_entry.grid(row=1, column=1, padx=5, pady=5, columnspan=5)

            find_button = tk.Button(self.find_replace_window, text="Find", command=self.find_matches)
            find_button.grid(row=2, column=0, padx=5, pady=15)

            find_all_button = tk.Button(self.find_replace_window, text="Find All", command=self.find_all_matches)
            find_all_button.grid(row=2, column=1, padx=5, pady=5)

            empty_label = tk.Label(self.find_replace_window, text="")
            empty_label.grid(row=2, column=2, padx=20)  # Add an empty label for spacing

            replace_button = tk.Button(self.find_replace_window, text="Replace", command=self.replace_text)
            replace_button.grid(row=2, column=3, padx=5, pady=5)

            replace_all_button = tk.Button(self.find_replace_window, text="Replace All", command=self.replace_all_text)
            replace_all_button.grid(row=2, column=4, padx=5, pady=5)

            nav_frame = tk.Frame(self.find_replace_window)
            nav_frame.grid(row=5, column=3, columnspan=2, padx=5, pady=15)

            self.first_match_button = tk.Button(nav_frame, text="|<<", command=self.go_to_first_match, state=tk.DISABLED)
            self.first_match_button.pack(side=tk.LEFT)

            self.prev_match_button = tk.Button(nav_frame, text="<<", command=self.go_to_prev_match, state=tk.DISABLED)
            self.prev_match_button.pack(side=tk.LEFT)

            self.next_match_button = tk.Button(nav_frame, text=">>", command=self.go_to_next_match, state=tk.DISABLED)
            self.next_match_button.pack(side=tk.LEFT)

            self.last_match_button = tk.Button(nav_frame, text=">>|", command=self.go_to_last_match, state=tk.DISABLED)
            self.last_match_button.pack(side=tk.LEFT)

            match_frame = tk.Frame(self.find_replace_window)
            match_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

            self.current_match_label = tk.Label(match_frame, text="Match: 0 ")
            self.current_match_label.pack(side=tk.LEFT)

            self.total_matches_label = tk.Label(match_frame, text="/ 0")
            self.total_matches_label.pack(side=tk.LEFT)

            self.find_replace_toggle = True
            self.find_replace_window.protocol("WM_DELETE_WINDOW", self.close_find_replace_window)

            # Restore the original text and selection range
            if original_text is not None:
                if self.text_display.tag_ranges("sel"):
                    self.text_display.delete("1.0", tk.END)
                    self.text_display.insert("1.0", original_text)
                    self.text_display.tag_add("sel", start_index, end_index)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while opening the Find and Replace window: {e}")
            self.error_logging(f"An error occurred while opening the Find and Replace window: {e}")

    def close_find_replace_window(self):
        self.find_replace_toggle = False
        self.find_replace_window.destroy()

    def find_matches(self):
        try:
            search_term = self.search_entry.get()
            self.find_replace_matches_df = pd.DataFrame(columns=["Index", "Page"])

            for index, row in self.main_df.iterrows():
                active_category = self.get_active_category(row["Index"])
                text = row[active_category]
                if pd.notna(text) and search_term in text:
                    self.find_replace_matches_df = pd.concat([self.find_replace_matches_df, pd.DataFrame({"Index": [index], "Page": [row["Index"]]})], ignore_index=True)

            if not self.find_replace_matches_df.empty:
                self.link_nav = self.find_replace_matches_df.iloc[0]["Page"]
                self.first_match_button.config(state=tk.NORMAL)
                self.prev_match_button.config(state=tk.NORMAL)
                self.next_match_button.config(state=tk.NORMAL)
                self.last_match_button.config(state=tk.NORMAL)
                self.navigate_images(direction=0)
                self.highlight_text()

            self.update_matches_counter()   
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while finding matches: {e}")
            self.error_logging(f"An error occurred while finding matches: {e}")

    def update_matches_counter(self):
        # Find the row index in find_replace_matches_df where the value of "Index" matches self.page_counter - 1
        current_row_index = self.find_replace_matches_df.index[self.find_replace_matches_df["Index"] == self.page_counter].tolist()

        if current_row_index:
            # Set the current match label to the current row index + 1
            self.current_match_label.config(text=f"Match(s): {current_row_index[0] + 1}")
        else:
            self.current_match_label.config(text="Match(s): 0")

        self.total_matches_label.config(text=f"/ {len(self.find_replace_matches_df)}")
    
    def find_all_matches(self):
        self.find_matches()

    def go_to_first_match(self):
        if not self.find_replace_matches_df.empty:
            self.link_nav = int(self.find_replace_matches_df.iloc[0]["Page"])
            self.navigate_images(direction=0)
        
        self.update_matches_counter()    

    def go_to_prev_match(self):
        if not self.find_replace_matches_df.empty:
            current_index = self.page_counter
            prev_match_index = self.find_replace_matches_df[self.find_replace_matches_df["Index"] < current_index]["Index"].max()
            
            if not pd.isna(prev_match_index):
                self.link_nav = int(prev_match_index)
                self.navigate_images(direction=0)
        self.update_matches_counter()

    def go_to_next_match(self):
        if not self.find_replace_matches_df.empty:
            current_index = self.page_counter
            next_match_index = self.find_replace_matches_df[self.find_replace_matches_df["Index"] > current_index]["Index"].min()
            
            if pd.notna(next_match_index):
                self.link_nav = int(next_match_index)
                self.navigate_images(direction=0)
            else:  # If no next match, wrap around to first match
                self.go_to_first_match()
        self.update_matches_counter()

    def go_to_last_match(self):
        if not self.find_replace_matches_df.empty:
            self.link_nav = int(self.find_replace_matches_df.iloc[-1]["Page"])
            self.navigate_images(direction=0)
        self.update_matches_counter()

    def highlight_text(self):
        search_term = self.search_entry.get()
        text_widget = self.text_display
        text_widget.tag_remove("highlight", "1.0", tk.END)

        if search_term:
            start_index = "1.0"
            while True:
                start_index = text_widget.search(search_term, start_index, tk.END, nocase=True)  # Add nocase=True for case-insensitive search
                if not start_index:
                    break
                end_index = f"{start_index}+{len(search_term)}c"
                text_widget.tag_add("highlight", start_index, end_index)
                start_index = end_index
            text_widget.tag_config("highlight", background="yellow")

    def replace_text(self):
        search_term = self.search_entry.get()
        replace_term = self.replace_entry.get()
        
        # Get the current text content
        current_text = self.text_display.get("1.0", tk.END)
        
        # Perform the replacement
        new_text = current_text.replace(search_term, replace_term)
        
        # Update the text display
        self.text_display.delete("1.0", tk.END)
        self.text_display.insert("1.0", new_text)
        
        # Update the DataFrame
        active_category = self.get_active_category(self.page_counter)
        self.main_df.loc[self.page_counter, active_category] = new_text.strip()
        
        # Refresh the highlighting
        self.highlight_text()

    def replace_all_text(self):
        if messagebox.askyesno("Replace All", "Are you sure you want to replace all occurrences? This action cannot be undone."):
            search_term = self.search_entry.get()
            replace_term = self.replace_entry.get()
            
            # Process all matches in the DataFrame
            for index, row in self.find_replace_matches_df.iterrows():
                active_page = row["Index"]
                active_category = self.get_active_category(active_page)
                
                # Get the text content
                text = self.main_df.loc[active_page, active_category]
                if pd.notna(text):
                    # Perform the replacement
                    new_text = text.replace(search_term, replace_term)
                    # Update the DataFrame
                    self.main_df.loc[active_page, active_category] = new_text
            
            # Update the current display if we're on one of the modified pages
            if self.page_counter in self.find_replace_matches_df["Index"].values:
                self.load_text()
                self.highlight_text()
            
            # Update the find/replace matches
            self.find_matches()

# AI Functions to process images and text for transcription

    def ai_function(self, all_or_one_flag="All Pages", ai_job="HTR", batch_size=50):
        self.toggle_button_state()

        responses_dict = {} # Store the responses with their row index
        futures_to_index = {} # Store the futures with their row index
        processed_rows = 0 # Initialize the number of processed rows

        if all_or_one_flag == "Current Page": # Process the current page only
            total_rows = 1
            row = self.page_counter
            batch_df = self.main_df.loc[[row]]
            if ai_job == "HTR":
                progress_window, progress_bar, progress_label = self.create_progress_window("Applying HTR to Current Page...")
            elif ai_job == "Correct":
                progress_window, progress_bar, progress_label = self.create_progress_window("Correcting Current Page...")

        else: # Process all pages
            batch_df = self.main_df[self.main_df['Image_Path'].notna() & (self.main_df['Image_Path'] != '')]
            total_rows = len(batch_df)
            if ai_job == "HTR":
                progress_window, progress_bar, progress_label = self.create_progress_window("Applying HTR to All Pages...")
            elif ai_job == "Correct":
                progress_window, progress_bar, progress_label = self.create_progress_window("Correcting All Pages...")
    
        if total_rows == 0: # Display a warning if no images are available for processing
            self.close_progress_window(progress_window)
            messagebox.showwarning("No Images", "No images are available for processing.")
            return

        self.update_progress(progress_bar, progress_label, processed_rows, total_rows) # Update the progress bar and label

        # Process the images in batches
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            for i in range(0, total_rows, batch_size):
                batch_df_subset = batch_df.iloc[i:i+batch_size]
                
                for index, row_data in batch_df_subset.iterrows():
                    image_path = row_data['Image_Path'] # Get the image path from the DataFrame

                    if image_path is not None and os.path.exists(image_path):
                        with open(image_path, "rb") as image_file:
                            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                    else:
                        image_base64 = None
                    if ai_job == "HTR":
                        text_to_process = ""
                        temp = 0.0
                        val_text = self.HTR_val_text
                        engine = self.HTR_model
                        user_prompt = self.HTR_user_prompt
                        system_prompt = self.HTR_system_prompt
                    elif ai_job == "Correct":
                        text_to_process = row_data['Original_Text']
                        temp = 0.0
                        val_text = self.correct_val_text
                        engine = self.correct_model
                        user_prompt = self.correct_user_prompt
                        system_prompt = self.correct_system_prompt

                    if "gpt" in engine.lower():
                        futures_to_index[executor.submit(self.send_to_gpt4_api, system_prompt, user_prompt, temp, image_base64, text_to_process, val_text, engine, index, api_timeout=80)] = index
                    elif "gemini" in engine.lower():
                        futures_to_index[executor.submit(self.send_to_gemini_api, system_prompt, user_prompt, temp, image_path, text_to_process, val_text, engine, index, api_timeout=80)] = index
                        time.sleep(1)
                    elif "claude" in engine.lower():
                        futures_to_index[executor.submit(asyncio.run, self.run_send_to_claude_api(system_prompt, user_prompt, temp, image_base64, text_to_process, val_text, engine, index, False, api_timeout=80))] = index

            try:
                for future in as_completed(futures_to_index):
                    try:
                        result = future.result()
                        if result and len(result) == 2: # Check if the result is valid; the result should be a tuple with two elements
                            response, index = future.result()  # Unpack the response and row index
                            responses_dict[index] = response  # Store the response with its row index
                            processed_rows += 1
                            self.update_progress(progress_bar, progress_label, processed_rows, total_rows)
                        else:
                            responses_dict[index] = ""  # Store an empty string if the response is invalid
                            processed_rows += 1
                            self.error_logging(f"HTR Function: An error occurred while processing row {futures_to_index[future]}")

                    except Exception as e:
                        responses_dict[index] = ""  # Store an empty string if an error occurs
                        # Use a messagebox to display an error
                        messagebox.showerror("Error", f"An error occurred while processing row {futures_to_index[future]}: {e}")
                        self.error_logging(f"HTR Function: An error occurred while processing row {futures_to_index[future]}: {e}")   

            finally:
                self.close_progress_window(progress_window)

                # Process the data from the futures that completed successfully
                error_count = 0
                if all_or_one_flag == "Current Page":
                    if row in responses_dict:
                        if responses_dict[row] == "Error":
                            error_count += 1
                        else:                           
                            if ai_job == "HTR":
                                self.main_df.at[row, 'Original_Text'] = responses_dict[row]
                                self.main_df.at[row, 'Text_Toggle'] = "Original Text"
                            elif ai_job == "Correct":
                                self.main_df.at[row, 'Initial_Draft_Text'] = responses_dict[row]
                                self.main_df.at[row, 'Text_Toggle'] = "Initial Draft"                            
                else:
                    for index, response in responses_dict.items():
                        if response == "Error":
                            error_count += 1
                        else:
                            if ai_job == "HTR":
                                self.main_df.at[index, 'Original_Text'] = response
                                self.main_df.at[index, 'Text_Toggle'] = "Original Text"
                            elif ai_job == "Correct":
                                self.main_df.at[index, 'Initial_Draft_Text'] = response
                                self.main_df.at[index, 'Text_Toggle'] = "Initial Draft"
                self.load_text()
                self.counter_update()
                self.toggle_button_state()

                # Display message box if errors were found
                if error_count > 0:
                    if all_or_one_flag == "Current Page":
                        messagebox.showwarning("HTR Error", f"An error occurred while processing the current page.")
                    else:
                        messagebox.showwarning("HTR Errors", f"Errors occurred while processing {error_count} page(s).")

# API Calls to OpenAI, Google, and Anthropic to process text and images for transcription and analysis

    def send_to_gpt4_api(self, system_prompt, user_prompt, temp, image_base64, text_to_process, val_text, engine, index, formatting_function=False, api_timeout=25.0, max_retries=3, retries=0):
        
        api_key = self.openai_api_key

        if api_key is None:
            raise ValueError("OpenAI API key not found in the API_Keys.txt file.")
       
        client = OpenAI(
            api_key=api_key,
            timeout=api_timeout,
            )
        
        if formatting_function:
            populated_user_prompt = f"""{user_prompt}"""
        else:
            # Populate the user prompt with the variables
            populated_user_prompt = user_prompt.format(text_to_process=text_to_process)

        while retries < max_retries:
            try:
                if image_base64 is not None:
                    messages = [
                        {"role": "system", "content": f"""{system_prompt}"""},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": populated_user_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}",
                                        "detail": "high"
                                    },
                                },
                            ],
                        }
                    ]
                else:
                    messages = [
                        {"role": "system", "content": f"""{system_prompt}"""},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": populated_user_prompt},
                            ],
                        }
                    ]

                message = client.chat.completions.create(
                    model=engine,
                    temperature=temp,
                    messages=messages,
                    max_tokens=4000
                )

                response = message.choices[0].message.content

                if val_text == "None":
                    return response, index
                elif val_text != "None" and val_text in response:
                    # strip val_text_a from the start of the response
                    response = response.split(val_text, 1)[1]
                    return response, index
                else:
                    print("Response does not contain the expected text.")
                    retries += 1
                    continue

            except openai.APITimeoutError as e:
                print(e)
                retries += 1
                continue

            except openai.APIError as e:
                print(e)
                retries += 1
                continue

        return "Error", index
    
    def send_to_gemini_api(self, system_prompt, user_prompt, temp, image_path, text_to_process, val_text, engine, index, formatting_function=False, api_timeout=120.0, max_retries=3, retries=0):
        
        genai.configure(api_key=self.google_api_key)

        if not self.google_api_key:
            raise ValueError("Google API key not found or invalid")

        model = genai.GenerativeModel(
            model_name=engine,
            system_instruction=f"""{system_prompt}""")

        if formatting_function:
            populated_user_prompt = f"""{user_prompt}"""
        else:
            populated_user_prompt = user_prompt.format(text_to_process=text_to_process)

        if image_path is not None:
            image1 = {
                'mime_type': 'image/jpeg',
                'data': Path(image_path).read_bytes()
            }

        while retries < max_retries:
            try:
                if image_path is not None: 
                    response = model.generate_content([populated_user_prompt, image1],
                        safety_settings={
                            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                        }
                    )
                else:
                    response = model.generate_content([populated_user_prompt],
                        safety_settings={
                            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                        }
                    )

                # If we have a valid response
                response_text = response.text

                if response_text:
                    if val_text == "None":
                        return response_text, index
                    elif val_text != "None" and val_text in response_text:
                        response_text = response_text.split(val_text, 1)[1]
                        return response_text, index
                    else:
                        print("Validation Text Not Found")
                        retries += 1
                        continue
                else:
                    print("No Response from API")
                    retries += 1
                    continue
            except Exception as e:
                print(f"Error: {e}")
                                
                retries += 1
                continue

        return "Error", index

    async def send_to_claude_api_in_parallel(self, system_prompt, user_prompt, temp, image_base64, text_to_process, val_text, engine, index, formatting_function=False, api_timeout=120.0, function_max_retries=3, retries=0):    
        async with AsyncAnthropic(api_key=self.anthropic_api_key, max_retries=0, timeout=api_timeout) as client:    
            try:
                if formatting_function:
                    populated_user_prompt = f"""{user_prompt}"""

                else:
                    # Populate the user prompt with the variables
                    populated_user_prompt = user_prompt.format(text_to_process=text_to_process)

                while retries < function_max_retries:
                    try:
                        if image_base64 is not None:
                            message = await client.messages.create(
                                    max_tokens=4000,
                                    messages=[
                                        {
                                            "role": "user",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": populated_user_prompt
                                                },
                                                {
                                                    "type": "image",
                                                    "source": {
                                                        "type": "base64",
                                                        "media_type": "image/jpeg",
                                                        "data": image_base64,
                                                    },
                                                }
                                            ],
                                        }
                                    ],
                                    system=f"""{system_prompt}""",
                                    model=engine,
                                    temperature=temp,
                                    timeout=api_timeout,
                                )
                            
                        else:
                            message = await client.messages.create(
                                    max_tokens=4000,
                                    messages=[
                                        {
                                            "role": "user",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": populated_user_prompt
                                                }
                                            ],
                                        }
                                    ],
                                    system=f"""{system_prompt}""",
                                    model=engine,
                                    stream=False,
                                    temperature=temp,
                                    timeout=api_timeout,
                                )
                            
                        response = message.content[0].text


                        if val_text == "None":
                            return response, index
                        elif val_text != "None" and val_text in response:
                            response = response.split(val_text, 1)[1]
                            return response, index
                        else:
                            retries += 1
                            continue

                    except anthropic.APITimeoutError:
                        retries += 1
                        print("Timeout Error")
                        await asyncio.sleep(1)
                        continue

                    except anthropic.APIError as e:
                        retries += 1
                        print(e)
                        await asyncio.sleep(1)
                        continue
            except Exception as e:
                pass

        return "Error", index  # Return an empty string and the index when max retries are reached
    
# Main Loop
     
if __name__ == "__main__":

    app = App()
    app.mainloop()