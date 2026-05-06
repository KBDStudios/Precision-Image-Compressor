import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageSequence
import io
import webbrowser
import threading

# --- HEIF / HEIC Support Integration ---
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

# --- UI Configuration ---
MAIN_FONT = ("Segoe UI", 10)
BOLD_FONT = ("Segoe UI", 10, "bold")
TITLE_FONT = ("Segoe UI", 14, "bold")

class ImagePanel(ttk.Frame):
    """A reusable frame containing a canvas with zoom, magnifier, and animation tools."""
    def __init__(self, parent, title):
        super().__init__(parent)
        self.original_img = None
        self.current_pil_image = None
        self.tk_img = None
        self.scale_factor = 1.0
        self.magnifier_active = False
        
        # Animation states
        self.is_animated = False
        self.frames = []
        self.durations = []
        self.current_frame_idx = 0
        self.anim_job = None

        # Header
        self.lbl_title = ttk.Label(self, text=title, font=TITLE_FONT, foreground="#005a9e")
        self.lbl_title.pack(pady=5)
        
        self.lbl_info = ttk.Label(self, text="No image loaded", font=MAIN_FONT)
        self.lbl_info.pack()

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar, text="Zoom In (+)", command=self.zoom_in, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Zoom Out (-)", command=self.zoom_out, width=12).pack(side=tk.LEFT, padx=2)
        
        self.btn_mag = ttk.Button(toolbar, text="Magnifier: OFF", command=self.toggle_magnifier, width=15)
        self.btn_mag.pack(side=tk.LEFT, padx=2)
        
        # --- NEW MAGNIFIER POWER SLIDER ---
        ttk.Label(toolbar, text="Mag Power:").pack(side=tk.LEFT, padx=(5, 2))
        self.mag_power_var = tk.DoubleVar(value=2.0)
        self.mag_slider = ttk.Scale(toolbar, from_=1.5, to=10.0, orient=tk.HORIZONTAL, variable=self.mag_power_var, length=80)
        self.mag_slider.pack(side=tk.LEFT, padx=2)
        # ----------------------------------
        
        self.lbl_zoom = ttk.Label(toolbar, text="100%", font=BOLD_FONT)
        self.lbl_zoom.pack(side=tk.RIGHT, padx=5)

        # Canvas for Image
        frame_canvas = ttk.Frame(self)
        frame_canvas.pack(fill=tk.BOTH, expand=True)

        self.vbar = ttk.Scrollbar(frame_canvas, orient=tk.VERTICAL)
        self.hbar = ttk.Scrollbar(frame_canvas, orient=tk.HORIZONTAL)
        self.vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.hbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(frame_canvas, xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set, bg="#1e1e1e", cursor="arrow", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.vbar.config(command=self.canvas.yview)
        self.hbar.config(command=self.canvas.xview)

        # Magnifier assets
        self.img_id = self.canvas.create_image(0, 0, anchor="nw")
        self.lens_size = 150
        self.lens_id = self.canvas.create_image(0, 0, anchor="center", state="hidden")
        self.lens_rect_id = self.canvas.create_rectangle(0, 0, 0, 0, outline="#00a8ff", width=2, state="hidden")
        self.lens_photo = None

        # Bindings
        self.canvas.bind("<Motion>", self.update_magnifier)
        self.canvas.bind("<Leave>", self.hide_magnifier)

    def load_image(self, img_data, info_text):
        if self.anim_job:
            self.after_cancel(self.anim_job)
            self.anim_job = None

        self.original_img = Image.open(io.BytesIO(img_data))
        self.lbl_info.config(text=info_text)
        self.scale_factor = 1.0

        self.is_animated = getattr(self.original_img, "is_animated", False)
        
        if self.is_animated:
            self.frames = []
            self.durations = []
            for frame in ImageSequence.Iterator(self.original_img):
                self.frames.append(frame.copy())
                self.durations.append(frame.info.get('duration', 100) or 100)
            
            self.current_frame_idx = 0
            self.play_animation()
        else:
            self.current_pil_image = self.original_img
            self.redraw_image()

    def play_animation(self):
        self.current_frame_idx = (self.current_frame_idx + 1) % len(self.frames)
        self.current_pil_image = self.frames[self.current_frame_idx]
        self.redraw_image()
        
        dur = self.durations[self.current_frame_idx]
        self.anim_job = self.after(dur, self.play_animation)

    def redraw_image(self):
        if not self.current_pil_image: return
        
        new_w = max(1, int(self.current_pil_image.width * self.scale_factor))
        new_h = max(1, int(self.current_pil_image.height * self.scale_factor))
        
        resample = Image.Resampling.NEAREST if self.scale_factor >= 1.0 else Image.Resampling.LANCZOS
        resized = self.current_pil_image.resize((new_w, new_h), resample)
        
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.itemconfig(self.img_id, image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        self.lbl_zoom.config(text=f"{int(self.scale_factor * 100)}%")

    def zoom_in(self):
        if self.current_pil_image:
            self.scale_factor *= 1.25
            self.redraw_image()

    def zoom_out(self):
        if self.current_pil_image:
            self.scale_factor *= 0.8
            self.redraw_image()

    def toggle_magnifier(self):
        self.magnifier_active = not self.magnifier_active
        if self.magnifier_active:
            self.btn_mag.config(text="Magnifier: ON")
            self.canvas.config(cursor="crosshair")
        else:
            self.btn_mag.config(text="Magnifier: OFF")
            self.canvas.config(cursor="arrow")
            self.hide_magnifier(None)

    def update_magnifier(self, event):
        if not self.magnifier_active or not self.current_pil_image: return
        
        self.canvas.itemconfig(self.lens_id, state="normal")
        self.canvas.itemconfig(self.lens_rect_id, state="normal")
        
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        
        orig_x = cx / self.scale_factor
        orig_y = cy / self.scale_factor
        
        # Use dynamic zoom factor from slider
        current_zoom_factor = self.mag_power_var.get()
        half_crop = (self.lens_size / current_zoom_factor) / 2
        
        left, top = orig_x - half_crop, orig_y - half_crop
        right, bottom = orig_x + half_crop, orig_y + half_crop
        
        try:
            cropped = self.current_pil_image.crop((left, top, right, bottom))
            zoomed = cropped.resize((self.lens_size, self.lens_size), Image.Resampling.NEAREST)
            self.lens_photo = ImageTk.PhotoImage(zoomed)
            self.canvas.itemconfig(self.lens_id, image=self.lens_photo)
            self.canvas.coords(self.lens_id, cx, cy)
            offset = self.lens_size / 2
            self.canvas.coords(self.lens_rect_id, cx - offset, cy - offset, cx + offset, cy + offset)
        except Exception:
            pass

    def hide_magnifier(self, event):
        self.canvas.itemconfig(self.lens_id, state="hidden")
        self.canvas.itemconfig(self.lens_rect_id, state="hidden")


class ImageCompressorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Precision Image Compressor (Animated Edition)")
        self.geometry("1400x750") 
        
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        self.raw_image_data = None
        self.compressed_data = None
        self.original_size_bytes = 0
        self.min_size_bytes = 0
        self.total_frames = 1
        self.loading_win = None
        self.current_job_id = 0 # Tracks active threading jobs to prevent out-of-order rendering
        
        # Base supported formats
        self.supported_formats = ["JPEG", "PNG", "GIF", "BMP", "TIFF", "TGA", "WEBP", "AVIF"]
        
        if HEIF_AVAILABLE:
            self.supported_formats.extend(["HEIC", "HEIF"])

        self.setup_ui()

    def setup_ui(self):
        # --- TOP TOOLBAR ---
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill=tk.X)

        self.btn_open = ttk.Button(top_frame, text="Open Image", command=self.open_image, width=15)
        self.btn_open.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(top_frame, text="About", command=self.show_about, width=10).pack(side=tk.LEFT, padx=5)

        self.btn_export = tk.Button(top_frame, text="Export Image", command=self.export_image, width=15, 
                               bg="#2ea043", fg="white", font=BOLD_FONT, relief=tk.FLAT, cursor="hand2")
        self.btn_export.pack(side=tk.RIGHT, padx=5)

        # --- MAIN PANELS (Before / After) ---
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.panel_left = ImagePanel(paned, "Before (Original)")
        paned.add(self.panel_left, weight=1)

        self.panel_right = ImagePanel(paned, "After (Compressed)")
        paned.add(self.panel_right, weight=1)

        # --- BOTTOM COMPRESSION CONTROL ---
        control_frame = ttk.LabelFrame(self, text="Target Compression Size", padding=15)
        control_frame.pack(fill=tk.X, padx=10, pady=10, side=tk.BOTTOM)

        # Variables & Units
        self.target_val = tk.DoubleVar(value=0.0)
        self.current_unit = "KB"
        self.unit_var = tk.StringVar(value=self.current_unit)
        self.pad_var = tk.BooleanVar(value=True) 
        self.target_format_var = tk.StringVar(value="JPEG")
        self.play_anim_var = tk.BooleanVar(value=False) # Default to false
        self.target_frame_var = tk.IntVar(value=1)
        self.units = {"Bytes": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}

        # Row 1: Size Inputs, Checkbox, Format Selection & Target Frame
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, expand=True, pady=(0, 5))

        ttk.Label(row1, text="Target Size:", font=BOLD_FONT).pack(side=tk.LEFT, padx=(0, 10))

        self.spinbox = ttk.Spinbox(row1, from_=0, to=100000, increment=1, textvariable=self.target_val, width=12, command=self.sync_slider)
        self.spinbox.pack(side=tk.LEFT)
        self.spinbox.bind("<KeyRelease>", self.sync_slider)

        self.combo_unit = ttk.Combobox(row1, textvariable=self.unit_var, values=list(self.units.keys()), width=5, state="readonly")
        self.combo_unit.pack(side=tk.LEFT, padx=(5, 10))
        self.combo_unit.bind("<<ComboboxSelected>>", self.update_ranges)

        self.check_pad = ttk.Checkbutton(row1, text="Pad Bytes to Match Size", variable=self.pad_var)
        self.check_pad.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row1, text="Target Format:", font=BOLD_FONT).pack(side=tk.LEFT, padx=(5, 5))
        self.combo_format = ttk.Combobox(row1, textvariable=self.target_format_var, values=self.supported_formats, width=6, state="readonly")
        self.combo_format.pack(side=tk.LEFT)
        self.combo_format.bind("<<ComboboxSelected>>", self.on_format_change)

        # Play Animation Checkbox
        self.check_play_anim = ttk.Checkbutton(row1, text="Play Animation", variable=self.play_anim_var, command=self.on_play_anim_toggle)
        self.check_play_anim.pack(side=tk.LEFT, padx=(15, 5))

        # Target Frame Controls
        ttk.Label(row1, text="Target Frame:", font=BOLD_FONT).pack(side=tk.LEFT, padx=(5, 5))
        self.frame_spinbox = ttk.Spinbox(row1, from_=1, to=1, increment=1, textvariable=self.target_frame_var, width=5, command=self.on_frame_change)
        self.frame_spinbox.pack(side=tk.LEFT)
        self.frame_spinbox.bind("<KeyRelease>", self.on_frame_change)
        
        self.frame_slider = ttk.Scale(row1, from_=1, to=1, orient=tk.HORIZONTAL, variable=self.target_frame_var, command=self.on_frame_change_slider)
        self.frame_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))

        # Row 2: Slider & Load/Preview Button
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, expand=True, pady=(10, 0))

        self.slider = ttk.Scale(row2, from_=0, to=10000, orient=tk.HORIZONTAL, variable=self.target_val, command=self.sync_spinbox)
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 20))

        self.btn_preview = tk.Button(row2, text="Load / Preview Compression", command=self.apply_compression, width=30, 
                                bg="#0078d7", fg="white", font=BOLD_FONT, relief=tk.FLAT, cursor="hand2")
        self.btn_preview.pack(side=tk.RIGHT)

    def set_ui_state(self, is_animating):
        """Grays out or restores the UI dynamically."""
        state = "disabled" if is_animating else "normal"
        readonly_state = "disabled" if is_animating else "readonly"

        self.spinbox.config(state=state)
        
        # Explicitly control ttk.Combobox states so they gray out correctly
        if is_animating:
            self.combo_unit.state(["disabled"])
            self.combo_format.state(["disabled"])
        else:
            self.combo_unit.state(["!disabled", "readonly"])
            self.combo_format.state(["!disabled", "readonly"])
            
        self.combo_unit.config(state=readonly_state)
        self.combo_format.config(state=readonly_state)
        
        self.check_pad.config(state=state)
        self.slider.config(state=state)
        self.btn_preview.config(state=state)
        
        if is_animating:
            self.frame_spinbox.config(state="disabled")
            self.frame_slider.config(state="disabled")

    def update_ui_state(self):
        """Manages the logic for the Checkbox and Frame controls."""
        target_fmt = self.target_format_var.get()
        supports_anim = target_fmt in ["WEBP", "TIFF", "AVIF", "GIF"]
        is_source_anim = self.total_frames > 1

        if not supports_anim or not is_source_anim:
            self.check_play_anim.config(state=tk.DISABLED)
            self.play_anim_var.set(False)
        else:
            self.check_play_anim.config(state=tk.NORMAL)

        if not self.play_anim_var.get():
            if not is_source_anim:
                self.frame_spinbox.config(state="disabled")
                self.frame_slider.config(state=tk.DISABLED)
            else:
                self.frame_spinbox.config(state="normal")
                self.frame_slider.config(state=tk.NORMAL)

    def show_loading_screen(self):
        """Displays a modal loading overlay to prevent main window interaction."""
        self.loading_win = tk.Toplevel(self)
        self.loading_win.title("Processing...")
        self.loading_win.geometry("300x100")
        self.loading_win.transient(self) 
        self.loading_win.grab_set() 
        
        self.loading_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 50
        self.loading_win.geometry(f"+{x}+{y}")
        self.loading_win.protocol("WM_DELETE_WINDOW", lambda: None) 
        
        ttk.Label(self.loading_win, text="Compressing image, please wait...", font=MAIN_FONT).pack(pady=15)
        self.progress = ttk.Progressbar(self.loading_win, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=20)
        self.progress.start(10)
        
        # Disable buttons temporarily during load
        self.check_play_anim.config(state=tk.DISABLED)
        self.btn_preview.config(state=tk.DISABLED)
        self.btn_export.config(state=tk.DISABLED)
        self.btn_open.config(state=tk.DISABLED)

    def hide_loading_screen(self):
        """Closes the loading overlay and returns the UI to the correct state."""
        if self.loading_win:
            self.progress.stop()
            self.loading_win.grab_release()
            self.loading_win.destroy()
            self.loading_win = None
            
        self.btn_export.config(state=tk.NORMAL)
        self.btn_open.config(state=tk.NORMAL)
        
        # Readjust UI based on if animation is checked
        is_animating = self.play_anim_var.get()
        self.set_ui_state(is_animating)
        self.update_ui_state()

    def on_play_anim_toggle(self):
        # Update immediately so sliders gray out
        is_animating = self.play_anim_var.get()
        self.set_ui_state(is_animating)
        self.update_ui_state()
        
        self._update_frame_limits()
        self.apply_compression()

    def _update_frame_limits(self):
        if not self.raw_image_data: return
        img = Image.open(io.BytesIO(self.raw_image_data))
        target_fmt = self.target_format_var.get()
        self.min_size_bytes = self.calculate_minimum_size(img, target_fmt)
        self.update_ranges()

    def sync_slider(self, *args):
        try:
            val = float(self.target_val.get())
            self.slider.set(val)
        except ValueError:
            pass

    def sync_spinbox(self, *args):
        try:
            val = float(self.slider.get())
            self.target_val.set(round(val, 6)) 
        except ValueError:
            pass
            
    def on_frame_change(self, *args):
        try:
            val = int(self.target_frame_var.get())
            self.frame_slider.set(val)
            self._update_frame_limits()
            self.apply_compression(show_loading=False)
        except ValueError:
            pass

    def on_frame_change_slider(self, *args):
        try:
            val = round(self.frame_slider.get())
            self.target_frame_var.set(val)
            self._update_frame_limits()
            self.apply_compression(show_loading=False)
        except ValueError:
            pass

    def update_ranges(self, *args):
        new_unit = self.unit_var.get()
        old_multiplier = self.units[self.current_unit]
        new_multiplier = self.units[new_unit]
        
        if new_unit == "GB":
            self.spinbox.config(increment=0.0001)
        elif new_unit == "MB":
            self.spinbox.config(increment=0.01)
        else:
            self.spinbox.config(increment=1)
            
        if self.original_size_bytes > 0:
            max_in_new_unit = self.original_size_bytes / new_multiplier
            min_in_new_unit = self.min_size_bytes / new_multiplier
            
            self.spinbox.config(from_=min_in_new_unit, to=max_in_new_unit)
            self.slider.config(from_=min_in_new_unit, to=max_in_new_unit)
            
            current_bytes = self.target_val.get() * old_multiplier
            new_val = current_bytes / new_multiplier
            
            new_val = max(min_in_new_unit, min(new_val, max_in_new_unit))
            self.target_val.set(round(new_val, 6)) 
            self.sync_slider()
            
        self.current_unit = new_unit

    def on_format_change(self, event=None):
        if not self.raw_image_data: return
        self.update_ui_state()
        self._update_frame_limits()
        self.apply_compression()

    def format_bytes(self, size):
        if size < 1024: return f"{size} Bytes"
        elif size < 1024 ** 2: return f"{size / 1024:.2f} KB"
        elif size < 1024 ** 3: return f"{size / (1024 ** 2):.2f} MB"
        else: return f"{size / (1024 ** 3):.2f} GB"

    def _process_frame_colors(self, img, target_format):
        if target_format == "JPEG" and img.mode in ("RGBA", "P"):
            return img.convert("RGB")
        elif target_format == "BMP" and img.mode in ("RGBA", "P"):
            return img.convert("RGB")
        elif target_format == "WEBP" and img.mode == "P":
            return img.convert("RGBA")
        return img

    def calculate_minimum_size(self, img, target_format):
        """Runs a hidden max-compression pass to find the absolute floor byte size"""
        out_buffer = io.BytesIO()
        is_anim = getattr(img, "is_animated", False)
        supports_anim = target_format in ["WEBP", "TIFF", "AVIF", "GIF"]
        play_anim = self.play_anim_var.get()
        
        save_fmt = "HEIF" if target_format in ["HEIC", "HEIF"] else target_format

        try:
            if is_anim and supports_anim and play_anim:
                frames = []
                img.seek(0)
                for f in ImageSequence.Iterator(img):
                    new_size = (max(1, int(img.width * 0.01)), max(1, int(img.height * 0.01)))
                    f_proc = self._process_frame_colors(f, save_fmt)
                    frames.append(f_proc.resize(new_size, Image.Resampling.LANCZOS))
                
                kwargs = {"save_all": True, "append_images": frames[1:]}
                if save_fmt in ["WEBP", "GIF"]:
                    kwargs["duration"] = img.info.get('duration', 100)
                    kwargs["loop"] = img.info.get('loop', 0)
                
                frames[0].save(out_buffer, format=save_fmt, **kwargs)
            else:
                if is_anim: 
                    target_f = max(0, int(self.target_frame_var.get()) - 1)
                    try: img.seek(target_f)
                    except EOFError: img.seek(0)
                
                if save_fmt in ["JPEG", "JPG"]:
                    img = self._process_frame_colors(img, save_fmt)
                    img.save(out_buffer, format="JPEG", quality=1)
                else:
                    new_size = (max(1, int(img.width * 0.01)), max(1, int(img.height * 0.01)))
                    temp_img = self._process_frame_colors(img, save_fmt)
                    temp_img = temp_img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    if save_fmt == "PNG":
                        temp_img.save(out_buffer, format="PNG", optimize=True)
                    else:
                        temp_img.save(out_buffer, format=save_fmt)
                        
        except Exception:
            return 100 
            
        return min(out_buffer.tell(), max(1, self.original_size_bytes - 100))

    def open_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Supported Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tga;*.webp;*.heic;*.heif;*.avif;*.gif")])
        if not filepath: return

        with open(filepath, 'rb') as f:
            self.raw_image_data = f.read()

        self.original_size_bytes = len(self.raw_image_data)
        
        temp_img = Image.open(io.BytesIO(self.raw_image_data))
        original_format = temp_img.format if temp_img.format else "PNG"
        if original_format not in self.supported_formats:
            original_format = "PNG"
            
        self.target_format_var.set(original_format)
        
        self.total_frames = getattr(temp_img, "n_frames", 1)
        self.frame_spinbox.config(from_=1, to=self.total_frames)
        self.frame_slider.config(from_=1, to=self.total_frames)
        self.target_frame_var.set(1)
        
        # Always default animation to OFF when opening a new file
        self.play_anim_var.set(False)
        self.set_ui_state(is_animating=False)
        self.update_ui_state()

        self.min_size_bytes = self.calculate_minimum_size(temp_img, original_format)

        info = f"{original_format} | {temp_img.width}x{temp_img.height} | {self.format_bytes(self.original_size_bytes)}"
        if self.total_frames > 1:
            info += f" | {self.total_frames} Frames"

        self.panel_left.load_image(self.raw_image_data, info)
        
        max_in_current = self.original_size_bytes / self.units[self.current_unit]
        min_in_current = self.min_size_bytes / self.units[self.current_unit]
        
        self.spinbox.config(from_=min_in_current, to=max_in_current)
        self.slider.config(from_=min_in_current, to=max_in_current)
        
        self.target_val.set(round(max_in_current, 6))
        self.sync_slider()

        if self.panel_right.anim_job:
            self.panel_right.after_cancel(self.panel_right.anim_job)
            self.panel_right.anim_job = None
        self.panel_right.current_pil_image = None
        self.panel_right.canvas.itemconfig(self.panel_right.img_id, image="")
        self.panel_right.lbl_info.config(text="Ready to compress")
        self.compressed_data = None

    def apply_compression(self, show_loading=True):
        """Gathers parameters safely on the main thread and starts the worker thread."""
        if not self.raw_image_data: return

        try:
            val = float(self.target_val.get())
            max_val = self.original_size_bytes / self.units[self.unit_var.get()]
            min_val = self.min_size_bytes / self.units[self.unit_var.get()]
            
            if val > max_val: val = max_val
            if val < min_val: val = min_val
                
            self.target_val.set(round(val, 6))
            target_bytes = int(val * self.units[self.unit_var.get()])
        except ValueError:
            return

        self.current_job_id += 1
        
        params = {
            "target_bytes": target_bytes,
            "target_fmt": self.target_format_var.get(),
            "play_anim": self.play_anim_var.get(),
            "target_frame": int(self.target_frame_var.get()),
            "pad_bytes": self.pad_var.get(),
            "job_id": self.current_job_id
        }

        if show_loading:
            self.show_loading_screen()
            
        threading.Thread(target=self._compression_worker, args=(params,), daemon=True).start()

    def _compression_worker(self, params):
        """Runs the heavy compression algorithm without blocking the Tkinter UI."""
        img = Image.open(io.BytesIO(self.raw_image_data))
        target_bytes = params["target_bytes"]
        target_fmt = params["target_fmt"]
        play_anim = params["play_anim"]
        pad_bytes = params["pad_bytes"]
        target_frame = max(0, params["target_frame"] - 1)
        job_id = params["job_id"]

        is_anim = getattr(img, "is_animated", False)
        supports_anim = target_fmt in ["WEBP", "TIFF", "AVIF", "GIF"]
        save_fmt = "HEIF" if target_fmt in ["HEIC", "HEIF"] else target_fmt

        out_buffer = io.BytesIO()
        best_data = None
        final_data = None

        try:
            if save_fmt in ["JPEG", "JPG"]:
                if is_anim: 
                    try: img.seek(target_frame)
                    except EOFError: img.seek(0)
                    
                img = self._process_frame_colors(img, "JPEG")
                
                low, high = 1, 100
                for _ in range(12): 
                    mid = (low + high) // 2
                    out_buffer.seek(0)
                    out_buffer.truncate(0)
                    img.save(out_buffer, format="JPEG", quality=mid)
                    size = out_buffer.tell()
                    
                    if size <= target_bytes:
                        best_data = out_buffer.getvalue()
                        low = mid + 1
                    else:
                        high = mid - 1
                        
            else: 
                scale = 1.0
                step = 0.05
                
                orig_frames = []
                if is_anim and supports_anim and play_anim:
                    img.seek(0)
                    for f in ImageSequence.Iterator(img):
                        orig_frames.append(f.copy())
                else:
                    if is_anim: 
                        try: img.seek(target_frame)
                        except EOFError: img.seek(0)
                    orig_frames = [img]

                while scale >= 0.01:
                    out_buffer.seek(0)
                    out_buffer.truncate(0)
                    
                    new_size = (int(max(1, img.width * scale)), int(max(1, img.height * scale)))
                    
                    processed_frames = []
                    for f in orig_frames:
                        f_proc = self._process_frame_colors(f, save_fmt)
                        processed_frames.append(f_proc.resize(new_size, Image.Resampling.LANCZOS))
                    
                    if is_anim and supports_anim and play_anim:
                        kwargs = {"save_all": True, "append_images": processed_frames[1:]}
                        if save_fmt in ["WEBP", "GIF"]:
                            kwargs["duration"] = img.info.get('duration', 100)
                            kwargs["loop"] = img.info.get('loop', 0)
                        processed_frames[0].save(out_buffer, format=save_fmt, **kwargs)
                    else:
                        if save_fmt == "PNG":
                            processed_frames[0].save(out_buffer, format="PNG", optimize=True)
                        else:
                            processed_frames[0].save(out_buffer, format=save_fmt)
                    
                    if out_buffer.tell() <= target_bytes:
                        best_data = out_buffer.getvalue()
                        break
                    
                    if scale > 0.01 and (scale - step) < 0.01:
                        scale = 0.01
                    else:
                        scale -= step

            if not best_data:
                final_data = out_buffer.getvalue()
            else:
                final_data = best_data

            if pad_bytes:
                current_size = len(final_data)
                if current_size < target_bytes:
                    padding_needed = target_bytes - current_size
                    final_data += (b'\x00' * padding_needed)

            self.after(0, lambda data=final_data, fmt=target_fmt, j_id=job_id: self._compression_success(data, fmt, j_id))

        except KeyError as e:
            self.after(0, lambda err=e, fmt=target_fmt: self._compression_error(f"Pillow is missing the backend plugin for {fmt}.\nDetailed error: {err}", "Format Error"))
        except Exception as e:
            self.after(0, lambda err=e: self._compression_error(f"An error occurred during compression:\n{err}", "Compression Error"))

    def _compression_success(self, final_data, target_fmt, job_id):
        """Called by the worker thread to safely update the UI upon success."""
        
        # Prevent older slider movements from overwriting the final movement
        if job_id != self.current_job_id:
            return 
            
        self.compressed_data = final_data
        
        res_img = Image.open(io.BytesIO(self.compressed_data))
        info = f"{target_fmt} | {res_img.width}x{res_img.height} | {self.format_bytes(len(self.compressed_data))}"
        if getattr(res_img, "is_animated", False):
            info += f" | {res_img.n_frames} Frames"
            
        self.panel_right.load_image(self.compressed_data, info)
        self.hide_loading_screen()

    def _compression_error(self, message, title):
        """Called by the worker thread to safely show errors on the main thread."""
        self.hide_loading_screen()
        messagebox.showerror(title, message)
        self.panel_right.lbl_info.config(text="Error rendering result")

    def export_image(self):
        if not self.raw_image_data:
            messagebox.showwarning("No Data", "Please open an image first.")
            return

        if not self.compressed_data:
            self.apply_compression()
            if self.loading_win is not None:
                return
            
        if not self.compressed_data:
            return

        fmt = self.target_format_var.get()
        ext = ".jpg" if fmt == "JPEG" else f".{fmt.lower()}"

        filepath = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=f"compressed_image{ext}",
            filetypes=[(f"{fmt} Image", f"*{ext}")]
        )

        if filepath:
            try:
                with open(filepath, 'wb') as f:
                    f.write(self.compressed_data)
                messagebox.showinfo("Success", f"Image successfully exported to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save image:\n{e}")

    def show_about(self):
        win = tk.Toplevel(self)
        win.title("About")
        win.geometry("400x320")
        win.grab_set()

        ttk.Label(win, text="Precision Image Compressor", font=TITLE_FONT).pack(pady=10)
        
        link_frame = ttk.Frame(win)
        link_frame.pack()
        ttk.Label(link_frame, text="Author: ").pack(side=tk.LEFT)
        lbl_link = tk.Label(link_frame, text="KBDStudios", fg="blue", cursor="hand2", font=("Segoe UI", 10, "underline"))
        lbl_link.pack(side=tk.LEFT)
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/KBDStudios"))

        desc = (
            "\nTechnical Details:\n"
            "This tool utilizes Python's Pillow library to compress images purely in memory. "
            "No cache folders are used, allowing for rapid real-time previews.\n\n"
            "For JPEGs, it uses a binary search algorithm to hunt for the exact "
            "quality integer required to hit the target byte size. For PNGs, BMPs, TGAs, and "
            "animated formats (WEBP, TIFF, GIF), it dynamically scales down the resolution of every frame "
            "until the target bytes are matched.\n\nExact padding applies raw null bytes."
        )
        ttk.Label(win, text=desc, wraplength=350, justify=tk.LEFT).pack(pady=10, padx=20)
        ttk.Button(win, text="Close", command=win.destroy).pack(side=tk.BOTTOM, pady=15)

if __name__ == "__main__":
    app = ImageCompressorApp()
    app.mainloop()