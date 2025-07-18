"""Main application window implementation."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from typing import Optional, Callable
from .components import StatusBar, ImageDropArea, ConfigurationPanel
from tkinterdnd2 import DND_FILES, TkinterDnD

logger = logging.getLogger(__name__)


class MainWindow:
    """Main application window for Finisher."""
    
    def __init__(self, title: str = "Finisher - AI Image Upscaling Tool"):
        """Initialize the main window.
        
        Args:
            title: Window title
        """
        self.root = TkinterDnD.Tk()
        self.root.title(title)
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Callbacks for external functionality
        self.on_image_dropped: Optional[Callable[[str], None]] = None
        self.on_file_selected: Optional[Callable[[str], None]] = None
        self.on_cancel_job: Optional[Callable[[], None]] = None
        self.on_emergency_stop: Optional[Callable[[], None]] = None
        self.on_config_changed: Optional[Callable[[dict], None]] = None
        
        self._setup_ui()
        self._setup_menu()
        self._setup_bindings()
        
        logger.info("Main window initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top section - Configuration panel
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.config_panel = ConfigurationPanel(config_frame)
        self.config_panel.on_config_changed = self._on_config_changed
        
        # Middle section - Image drop area
        drop_frame = ttk.LabelFrame(main_frame, text="Image Input", padding=10)
        drop_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.drop_area = ImageDropArea(drop_frame)
        self.drop_area.on_image_dropped = self._on_image_dropped
        self.drop_area.on_file_selected = self._on_file_selected
        
        # Bottom section - Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File browser button
        self.browse_button = ttk.Button(
            button_frame,
            text="Browse Files...",
            command=self._browse_files
        )
        self.browse_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Cancel job button
        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel Job",
            command=self._cancel_job,
            state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Emergency stop button
        self.emergency_button = ttk.Button(
            button_frame,
            text="Emergency Stop",
            command=self._emergency_stop,
            style="Emergency.TButton"
        )
        self.emergency_button.pack(side=tk.RIGHT)
        
        # Status bar at bottom
        self.status_bar = StatusBar(self.root)
        
        # Configure button styles
        style = ttk.Style()
        style.configure("Emergency.TButton", foreground="red")
        style.configure("Success.TButton", foreground="green")

        # Add tooltips and better visual feedback
        self._setup_tooltips()

    def _setup_tooltips(self) -> None:
        """Set up tooltips for UI elements."""
        # Simple tooltip implementation
        def create_tooltip(widget, text):
            def on_enter(event):
                tooltip = tk.Toplevel()
                tooltip.wm_overrideredirect(True)
                tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
                label = tk.Label(tooltip, text=text, background="lightyellow",
                               relief="solid", borderwidth=1, font=("Arial", 8))
                label.pack()
                widget.tooltip = tooltip

            def on_leave(event):
                if hasattr(widget, 'tooltip'):
                    widget.tooltip.destroy()
                    del widget.tooltip

            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        # Add tooltips to buttons
        create_tooltip(self.browse_button, "Browse for image files (Ctrl+O)")
        create_tooltip(self.cancel_button, "Cancel current processing job (Esc)")
        create_tooltip(self.emergency_button, "Emergency stop - interrupts any Auto1111 job")

        # Add tooltip to drop area
        create_tooltip(self.drop_area.drop_frame,
                      "Drop image files here or paste from clipboard (Ctrl+V)")

    def _setup_menu(self) -> None:
        """Set up the application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Image...", command=self._browse_files)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Paste Image", command=self._paste_image)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _setup_bindings(self) -> None:
        """Set up keyboard bindings."""
        self.root.bind('<Control-o>', lambda e: self._browse_files())
        self.root.bind('<Control-v>', lambda e: self._paste_image())
        self.root.bind('<Escape>', lambda e: self._cancel_job())
        self.root.bind('<<BrowseFiles>>', lambda e: self._browse_files())
    
    def _browse_files(self) -> None:
        """Open file browser dialog."""
        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp"),
            ("PNG files", "*.png"),
            ("JPEG files", "*.jpg *.jpeg"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=filetypes
        )
        
        if filename and self.on_file_selected:
            self.on_file_selected(filename)
    
    def _paste_image(self) -> None:
        """Handle paste image from clipboard."""
        try:
            from PIL import ImageGrab
            image = ImageGrab.grabclipboard()

            if image is None:
                messagebox.showwarning("Clipboard", "No image found in clipboard")
                return

            if not hasattr(image, 'save'):
                messagebox.showwarning("Clipboard", "Clipboard content is not an image")
                return

            # Create temporary file in docs/temp directory and trigger processing
            import tempfile
            import os
            from finisher.core.utils import get_docs_temp_dir

            docs_temp_dir = get_docs_temp_dir()
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.png',
                prefix='finisher_clipboard_',
                dir=docs_temp_dir
            )
            os.close(temp_fd)

            image.save(temp_path, 'PNG')

            if self.on_file_selected:
                self.on_file_selected(temp_path)

            # Schedule cleanup
            self.root.after(5000, lambda: self._cleanup_temp_file(temp_path))

        except ImportError:
            messagebox.showerror("Error", "PIL library not available for clipboard operations")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to paste image: {e}")

    def _cleanup_temp_file(self, file_path: str) -> None:
        """Clean up temporary file."""
        try:
            import os
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            pass  # Ignore cleanup errors
    
    def _on_image_dropped(self, file_path: str) -> None:
        """Handle image dropped event."""
        if self.on_image_dropped:
            self.on_image_dropped(file_path)
    
    def _on_file_selected(self, file_path: str) -> None:
        """Handle file selected event."""
        if self.on_file_selected:
            self.on_file_selected(file_path)
    
    def _on_config_changed(self, config: dict) -> None:
        """Handle configuration changed event."""
        if self.on_config_changed:
            self.on_config_changed(config)
    
    def _cancel_job(self) -> None:
        """Handle cancel job button."""
        if self.on_cancel_job:
            self.on_cancel_job()
    
    def _emergency_stop(self) -> None:
        """Handle emergency stop button."""
        result = messagebox.askyesno(
            "Emergency Stop",
            "This will interrupt any running Auto1111 job. Continue?",
            icon="warning"
        )
        
        if result and self.on_emergency_stop:
            self.on_emergency_stop()
    
    def _show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "About Finisher",
            "Finisher - AI Image Upscaling Tool\n\n"
            "Version: 0.0.0\n"
            "Author: illuminatianon\n\n"
            "Uses Automatic1111 API for AI-powered image upscaling."
        )
    
    def update_status(self, status: str, progress: Optional[float] = None) -> None:
        """Update status bar.
        
        Args:
            status: Status text
            progress: Progress value (0.0 to 1.0) or None to hide
        """
        self.status_bar.update_status(status, progress)
    
    def set_cancel_button_enabled(self, enabled: bool) -> None:
        """Enable or disable cancel button.
        
        Args:
            enabled: True to enable, False to disable
        """
        self.cancel_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def update_configuration_options(self, upscalers: list, models: list, 
                                   samplers: list, schedulers: list) -> None:
        """Update configuration panel options.
        
        Args:
            upscalers: List of available upscalers
            models: List of available models
            samplers: List of available samplers
            schedulers: List of available schedulers
        """
        self.config_panel.update_options(upscalers, models, samplers, schedulers)
    
    def get_configuration(self) -> dict:
        """Get current configuration from panel.
        
        Returns:
            Configuration dictionary
        """
        return self.config_panel.get_configuration()
    
    def run(self) -> None:
        """Start the GUI event loop."""
        logger.info("Starting GUI event loop")
        self.root.mainloop()
    
    def show_success_message(self, message: str) -> None:
        """Show success message to user.

        Args:
            message: Success message to display
        """
        messagebox.showinfo("Success", message)

        # Also update drop area with success feedback
        self.drop_area.set_status("✓ " + message, "green")

        # Reset status after a few seconds
        self.root.after(3000, lambda: self.drop_area.set_status(
            "Drop image files here\nor click to browse", "darkgray"
        ))

    def show_error_message(self, message: str) -> None:
        """Show error message to user.

        Args:
            message: Error message to display
        """
        messagebox.showerror("Error", message)

        # Also update drop area with error feedback
        self.drop_area.set_status("✗ " + message, "red")

        # Reset status after a few seconds
        self.root.after(5000, lambda: self.drop_area.set_status(
            "Drop image files here\nor click to browse", "darkgray"
        ))

    def show_processing_feedback(self, message: str) -> None:
        """Show processing feedback to user.

        Args:
            message: Processing message to display
        """
        self.drop_area.set_status("⏳ " + message, "blue")

    def reset_ui_state(self) -> None:
        """Reset UI to initial state."""
        self.set_cancel_button_enabled(False)
        self.update_status("Ready")
        self.drop_area.set_status(
            "Drop image files here\nor click to browse", "darkgray"
        )

    def destroy(self) -> None:
        """Destroy the window."""
        self.root.destroy()
