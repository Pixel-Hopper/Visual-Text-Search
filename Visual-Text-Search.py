import tkinter as tk
from tkinter import filedialog, messagebox
import easyocr
import torch
from PIL import Image, ImageDraw, ImageTk

# Check if CUDA (GPU) is available
use_gpu = torch.cuda.is_available()

# Initialize EasyOCR reader with GPU if available, else fallback to CPU
try:
    reader = easyocr.Reader(['en'], gpu=use_gpu)
    print("Using", "GPU" if use_gpu else "CPU")
except Exception as e:
    print(f"Error initializing EasyOCR: {e}")
    reader = easyocr.Reader(['en'], gpu=False)
    print("Falling back to CPU.")

# Store selected images
selected_images = []

# Function to browse and load multiple images
def browse_images():
    global selected_images
    file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
    if file_paths:
        selected_images.extend(file_paths)
        update_preview()

# Function to clear selected images
def clear_selected_images():
    global selected_images
    selected_images = []
    update_preview()

# Function to update preview panel
def update_preview():
    for widget in preview_frame.winfo_children():
        widget.destroy()

    for idx, img_path in enumerate(selected_images):
        try:
            img = Image.open(img_path)
            img.thumbnail((100, 100))
            img_tk = ImageTk.PhotoImage(img)

            label = tk.Label(preview_frame, image=img_tk)
            label.image = img_tk  # Keep reference
            label.grid(row=idx // 5, column=idx % 5, padx=5, pady=5)
        except Exception as e:
            print(f"Error loading image {img_path}: {e}")

# Function to search text in all selected images
def search_text_in_images():
    if not selected_images:
        messagebox.showerror("Error", "Please select images first!")
        return

    search_term = search_term_entry.get().strip().lower()
    if not search_term:
        messagebox.showerror("Error", "Please enter a search term!")
        return

    for img_path in selected_images:
        try:
            # Perform OCR
            result = reader.readtext(img_path)

            found = False
            img = Image.open(img_path)
            draw = ImageDraw.Draw(img)

            for (bbox, text, prob) in result:
                if search_term in text.lower():
                    found = True
                    bbox_points = [point for coord in bbox for point in coord]
                    draw.polygon(bbox_points, outline="red", width=2)

            if found:
                show_highlighted_image(img, img_path, search_term)
            else:
                messagebox.showinfo("Result", f"'{search_term}' not found in '{img_path.split('/')[-1]}'.")

        except Exception as e:
            messagebox.showerror("Error", f"Error processing {img_path}: {e}")

# Function to show highlighted image
def show_highlighted_image(img, title, search_term):
    window = tk.Toplevel(root)
    window.title(f"Found '{search_term}' in {title.split('/')[-1]}")
    window.geometry("800x600")

    canvas = tk.Canvas(window, bg='gray')
    canvas.pack(fill=tk.BOTH, expand=True)

    scroll_x = tk.Scrollbar(window, orient=tk.HORIZONTAL, command=canvas.xview)
    scroll_y = tk.Scrollbar(window, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
    scroll_x.pack(fill=tk.X, side=tk.BOTTOM)
    scroll_y.pack(fill=tk.Y, side=tk.RIGHT)

    canvas.bind("<Configure>", lambda e: update_image())

    zoom_level = [1.0]
    img_id = [None]
    img_tk = [None]

    def update_image():
        canvas_width = canvas.winfo_width()
        if canvas_width < 10:
            return

        base_width = canvas_width
        base_height = int(base_width / img.width * img.height)

        scaled_width = int(base_width * zoom_level[0])
        scaled_height = int(base_height * zoom_level[0])

        resized_img = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        img_tk[0] = ImageTk.PhotoImage(resized_img)

        canvas.delete("all")
        img_id[0] = canvas.create_image(0, 0, anchor="nw", image=img_tk[0])
        canvas.config(scrollregion=canvas.bbox(tk.ALL))

    def on_mousewheel(event):
        if event.delta > 0:
            zoom_level[0] *= 1.1
        else:
            zoom_level[0] *= 0.9
        zoom_level[0] = max(0.1, min(zoom_level[0], 10))
        update_image()

    pan_start = [0, 0]
    view_start = [0.0, 0.0]

    def start_pan(event):
        pan_start[0] = event.x
        pan_start[1] = event.y
        view_start[0] = canvas.xview()[0]
        view_start[1] = canvas.yview()[0]

    def do_pan(event):
        dx = event.x - pan_start[0]
        dy = event.y - pan_start[1]

        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        new_x = view_start[0] - dx / (canvas_width * 10)
        new_y = view_start[1] - dy / (canvas_height * 10)

        new_x = max(0, min(new_x, 1))
        new_y = max(0, min(new_y, 1))

        canvas.xview_moveto(new_x)
        canvas.yview_moveto(new_y)

    canvas.bind("<ButtonPress-1>", start_pan)
    canvas.bind("<B1-Motion>", do_pan)
    canvas.bind("<MouseWheel>", on_mousewheel)
    canvas.bind("<Button-4>", on_mousewheel)  # Linux scroll up
    canvas.bind("<Button-5>", on_mousewheel)  # Linux scroll down

    update_image()

# --- GUI Setup ---

root = tk.Tk()
root.title("")
root.geometry("640x360")

# Top Frame for buttons
top_frame = tk.Frame(root)
top_frame.pack(pady=10)

browse_button = tk.Button(top_frame, text="Images", command=browse_images)
browse_button.grid(row=0, column=0, padx=10)

search_term_entry = tk.Entry(top_frame, width=40)
search_term_entry.grid(row=0, column=1, padx=10)
search_term_entry.insert(0, "Enter text to search...")

search_button = tk.Button(top_frame, text="Search", command=search_text_in_images)
search_button.grid(row=0, column=2, padx=10)

clear_button = tk.Button(top_frame, text="Clear", command=clear_selected_images)
clear_button.grid(row=0, column=3, padx=10)

# Frame to preview images
preview_frame = tk.Frame(root)
preview_frame.pack(pady=10)

# Run main loop
root.mainloop()