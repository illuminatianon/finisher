"""GUI components for the main window."""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Callable, List
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    # Fallback if tkinterdnd2 is not available
    DND_FILES = None
    TkinterDnD = None

logger = logging.getLogger(__name__)


class StatusBar:
    """Status bar component for showing progress and status."""
    
    def __init__(self, parent: tk.Widget):
        """Initialize status bar.
        
        Args:
            parent: Parent widget
        """
        self.frame = ttk.Frame(parent)
        self.frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Status label
        self.status_label = ttk.Label(self.frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Initially hide progress bar
        self.progress_bar.pack_forget()
    
    def update_status(self, status: str, progress: Optional[float] = None) -> None:
        """Update status and progress.
        
        Args:
            status: Status text
            progress: Progress value (0.0 to 1.0) or None to hide
        """
        self.status_label.config(text=status)
        
        if progress is not None:
            self.progress_var.set(progress * 100)
            self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
        else:
            self.progress_bar.pack_forget()


class ProgressIndicator:
    """Standalone progress indicator component."""
    
    def __init__(self, parent: tk.Widget):
        """Initialize progress indicator.
        
        Args:
            parent: Parent widget
        """
        self.frame = ttk.Frame(parent)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.label = ttk.Label(self.frame, text="")
        self.label.pack()
    
    def update(self, progress: float, text: str = "") -> None:
        """Update progress indicator.
        
        Args:
            progress: Progress value (0.0 to 1.0)
            text: Optional text to display
        """
        self.progress_var.set(progress * 100)
        self.label.config(text=text)
    
    def show(self) -> None:
        """Show the progress indicator."""
        self.frame.pack(fill=tk.X, padx=5, pady=5)
    
    def hide(self) -> None:
        """Hide the progress indicator."""
        self.frame.pack_forget()


class ImageDropArea:
    """Drag and drop area for images."""
    
    def __init__(self, parent: tk.Widget):
        """Initialize image drop area.
        
        Args:
            parent: Parent widget
        """
        self.parent = parent
        self.on_image_dropped: Optional[Callable[[str], None]] = None
        self.on_file_selected: Optional[Callable[[str], None]] = None
        
        self._setup_ui()
        self._setup_drag_drop()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Main drop area
        self.drop_frame = tk.Frame(
            self.parent,
            bg="lightgray",
            relief=tk.SUNKEN,
            bd=2
        )
        self.drop_frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions label
        self.instructions = tk.Label(
            self.drop_frame,
            text="Drop image files here\nor click to browse",
            bg="lightgray",
            fg="darkgray",
            font=("Arial", 12)
        )
        self.instructions.pack(expand=True)
        
        # Bind click event
        self.drop_frame.bind("<Button-1>", self._on_click)
        self.instructions.bind("<Button-1>", self._on_click)
    
    def _setup_drag_drop(self) -> None:
        """Set up drag and drop functionality."""
        if TkinterDnD and DND_FILES:
            try:
                # Enable drag and drop
                self.drop_frame.drop_target_register(DND_FILES)
                self.drop_frame.dnd_bind('<<Drop>>', self._on_drop)
                self.drop_frame.dnd_bind('<<DragEnter>>', self._on_drag_enter)
                self.drop_frame.dnd_bind('<<DragLeave>>', self._on_drag_leave)

                logger.info("Drag and drop enabled")
            except Exception as e:
                logger.warning(f"Failed to enable drag and drop: {e}")
                # Don't re-raise the exception - just continue without drag and drop
        else:
            logger.warning("tkinterdnd2 not available, drag and drop disabled")
    
    def _on_click(self, event) -> None:
        """Handle click event to browse files."""
        # Trigger file browser through callback
        if self.on_file_selected:
            # Create a dummy event to trigger file browser
            # This will be caught by the main window
            self.parent.event_generate("<<BrowseFiles>>")
    
    def _on_drop(self, event) -> None:
        """Handle file drop event."""
        if not self.on_image_dropped:
            return
        
        try:
            # Get dropped files
            files = event.data.split()
            
            # Process first valid image file
            for file_path in files:
                # Remove curly braces if present
                file_path = file_path.strip('{}')
                
                if self._is_image_file(file_path):
                    self.on_image_dropped(file_path)
                    break
            
        except Exception as e:
            logger.error(f"Error handling drop event: {e}")
    
    def _on_drag_enter(self, event) -> None:
        """Handle drag enter event."""
        self.drop_frame.config(bg="lightblue")
        self.instructions.config(bg="lightblue", text="Drop image here")
    
    def _on_drag_leave(self, event) -> None:
        """Handle drag leave event."""
        self.drop_frame.config(bg="lightgray")
        self.instructions.config(bg="lightgray", text="Drop image files here\nor click to browse")
    
    def _is_image_file(self, file_path: str) -> bool:
        """Check if file is an image.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is an image
        """
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}
        return any(file_path.lower().endswith(ext) for ext in image_extensions)
    
    def set_status(self, text: str, color: str = "darkgray") -> None:
        """Set status text in the drop area.
        
        Args:
            text: Status text
            color: Text color
        """
        self.instructions.config(text=text, fg=color)


class ConfigurationPanel:
    """Configuration panel for processing settings."""
    
    def __init__(self, parent: tk.Widget):
        """Initialize configuration panel.
        
        Args:
            parent: Parent widget
        """
        self.parent = parent
        self.on_config_changed: Optional[Callable[[dict], None]] = None
        
        # Configuration variables
        self.upscaler_var = tk.StringVar()
        self.scale_var = tk.DoubleVar(value=2.5)
        self.denoising_var = tk.DoubleVar(value=0.15)
        self.tile_overlap_var = tk.IntVar(value=64)
        
        self._setup_ui()
        self._setup_bindings()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Create grid layout
        row = 0
        
        # Upscaler selection
        ttk.Label(self.parent, text="Upscaler:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10))
        self.upscaler_combo = ttk.Combobox(self.parent, textvariable=self.upscaler_var, state="readonly")
        self.upscaler_combo.grid(row=row, column=1, sticky=tk.EW, padx=(0, 20))
        
        # Scale factor
        ttk.Label(self.parent, text="Scale Factor:").grid(row=row, column=2, sticky=tk.W, padx=(0, 10))
        self.scale_spin = ttk.Spinbox(
            self.parent,
            from_=1.0,
            to=4.0,
            increment=0.1,
            textvariable=self.scale_var,
            width=10
        )
        self.scale_spin.grid(row=row, column=3, sticky=tk.W)
        
        row += 1
        
        # Denoising strength
        ttk.Label(self.parent, text="Denoising:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10))
        self.denoising_spin = ttk.Spinbox(
            self.parent,
            from_=0.0,
            to=1.0,
            increment=0.05,
            textvariable=self.denoising_var,
            width=10
        )
        self.denoising_spin.grid(row=row, column=1, sticky=tk.W)
        
        # Tile overlap
        ttk.Label(self.parent, text="Tile Overlap:").grid(row=row, column=2, sticky=tk.W, padx=(0, 10))
        self.tile_spin = ttk.Spinbox(
            self.parent,
            from_=0,
            to=256,
            increment=8,
            textvariable=self.tile_overlap_var,
            width=10
        )
        self.tile_spin.grid(row=row, column=3, sticky=tk.W)
        
        # Configure column weights
        self.parent.columnconfigure(1, weight=1)
        self.parent.columnconfigure(3, weight=1)
    
    def _setup_bindings(self) -> None:
        """Set up variable change bindings."""
        self.upscaler_var.trace('w', self._on_config_change)
        self.scale_var.trace('w', self._on_config_change)
        self.denoising_var.trace('w', self._on_config_change)
        self.tile_overlap_var.trace('w', self._on_config_change)
    
    def _on_config_change(self, *args) -> None:
        """Handle configuration change."""
        if self.on_config_changed:
            config = self.get_configuration()
            self.on_config_changed(config)
    
    def update_options(self, upscalers: List[str], models: List[str], 
                      samplers: List[str], schedulers: List[str]) -> None:
        """Update available options.
        
        Args:
            upscalers: List of upscaler names
            models: List of model names
            samplers: List of sampler names
            schedulers: List of scheduler names
        """
        # Update upscaler options
        self.upscaler_combo['values'] = upscalers
        if upscalers and not self.upscaler_var.get():
            self.upscaler_var.set(upscalers[0])
    
    def get_configuration(self) -> dict:
        """Get current configuration.
        
        Returns:
            Configuration dictionary
        """
        return {
            "upscaler": self.upscaler_var.get(),
            "scale_factor": self.scale_var.get(),
            "denoising_strength": self.denoising_var.get(),
            "tile_overlap": self.tile_overlap_var.get()
        }
    
    def set_configuration(self, config: dict) -> None:
        """Set configuration values.
        
        Args:
            config: Configuration dictionary
        """
        if "upscaler" in config:
            self.upscaler_var.set(config["upscaler"])
        if "scale_factor" in config:
            self.scale_var.set(config["scale_factor"])
        if "denoising_strength" in config:
            self.denoising_var.set(config["denoising_strength"])
        if "tile_overlap" in config:
            self.tile_overlap_var.set(config["tile_overlap"])
