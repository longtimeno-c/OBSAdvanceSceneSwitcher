import json
import time
import uuid
import threading
import websocket
import tkinter as tk
import ctypes
from tkinter import ttk, simpledialog
import os

# OBS WebSocket Config
OBS_HOST = "ws://OBSIP:port"  # Change to the IP and port of the OBS WebSocket server
PASSWORD = "Password"  # Your OBS WebSocket password

# Global Variables
scene_groups = {}
ws = None

# Add these constants near the top with other configs
SETTINGS_FILE = "obs_scene_switcher_settings.json"

# Minimize console window
def minimize_console():
    """Minimize console"""
    hWnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hWnd:
        ctypes.windll.user32.ShowWindow(hWnd, 6)

minimize_console()


def get_auth_response(password, challenge, salt):
    """Generate OBS authentication response."""
    import hashlib
    import base64
    hashed_secret = hashlib.sha256((password + salt).encode()).digest()
    auth_response = hashlib.sha256((base64.b64encode(hashed_secret).decode() + challenge).encode()).digest()
    return base64.b64encode(auth_response).decode()

class OBSController:
    def __init__(self, overlay):
        self.overlay = overlay
        self.canvas = None
        self.scenes = []
        self.active_rotations = set()
        self.current_scene = None
        self.hidden_scenes = {}  # Initialize empty dict
        
        # Load saved settings before anything else
        self.load_settings()
        
        # Configure the main window style
        self.overlay.configure(bg='#2b2b2b')  # Dark background
        self.overlay.option_add('*TLabelframe*Label.foreground', 'white')  # White text for group labels
        self.overlay.option_add('*TLabelframe.foreground', 'white')
        self.overlay.option_add('*TLabelframe.background', '#2b2b2b')
        
        # Add padding around the main window
        padding_frame = tk.Frame(self.overlay, bg='#2b2b2b')
        padding_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.main_frame = padding_frame  # Store reference to main frame
        self.connect()
        
        # Update scene groups after connection is established and settings are loaded
        self.overlay.after(1000, self.update_scene_groups)  # Add 1 second delay to ensure scenes are loaded

    def on_message(self, ws, message):
        data = json.loads(message)
        if data['op'] == 0:
            secret = data['d']['authentication']['challenge']
            salt = data['d']['authentication']['salt']
            auth_response = get_auth_response(PASSWORD, secret, salt)
            auth_payload = {'op': 1, 'd': {'rpcVersion': 1, 'authentication': auth_response, 'eventSubscriptions': 5}}
            ws.send(json.dumps(auth_payload))
        elif data['op'] == 2:
            scene_request_payload = {'op': 6, 'd': {'resource': 'ScenesService', 'requestType': 'GetSceneList', 'requestId': str(uuid.uuid4())}}
            ws.send(json.dumps(scene_request_payload))
        elif data['op'] == 7 and data['d']['requestType'] == 'GetSceneList':
            self.scenes = [scene['sceneName'] for scene in data['d']['responseData']['scenes']]
            self.overlay.after(0, lambda: self.populate_scene_buttons())
        elif data['op'] == 5 and data['d']['eventType'] == 'CurrentProgramSceneChanged':
            current_scene = data['d']['eventData']['sceneName']
            self.current_scene = current_scene
            self.update_scene_highlighting()
            self.update_overlay_visibility(current_scene)

    def connect(self):
        global ws
        ws = websocket.WebSocketApp(
            OBS_HOST,
            on_message=self.on_message,
            on_error=lambda ws, error: print(f"WebSocket Error: {error}"),
            on_close=lambda ws, status_code, msg: print(f"Connection Closed: {status_code}, {msg}"),
            on_open=lambda ws: print("Connected to OBS"),
        )
        threading.Thread(target=ws.run_forever, daemon=True).start()

    def send_switch_scene(self, scene_name):
        scene_switch_payload = {'op': 6, 'd': {'resource': 'ScenesService', 'requestType': 'SetCurrentProgramScene', 'requestData': {'sceneName': scene_name}, 'requestId': str(uuid.uuid4())}}
        ws.send(json.dumps(scene_switch_payload))
        self.current_scene = scene_name
        self.update_scene_highlighting()

    def populate_scene_buttons(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Create left and right frames with styling
        left_frame = tk.Frame(self.main_frame, bg='#2b2b2b')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        right_frame = tk.Frame(self.main_frame, bg='#2b2b2b')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        
        # Style the add group button
        add_group_btn = tk.Button(
            left_frame,
            text="+ Add Group",
            command=self.add_scene_group,
            bg='#4CAF50',
            fg='white',
            relief=tk.FLAT,
            font=('Segoe UI', 10, 'bold'),
            padx=10,
            pady=5
        )
        add_group_btn.pack(side=tk.TOP, anchor=tk.W, pady=(0, 10))
        
        # Add hover effect
        add_group_btn.bind('<Enter>', lambda e: add_group_btn.configure(bg=self.adjust_color('#4CAF50', -20)))
        add_group_btn.bind('<Leave>', lambda e: add_group_btn.configure(bg='#4CAF50'))
        
        # Style scene buttons
        for scene in self.scenes:
            btn = tk.Button(
                right_frame,
                text=scene,
                command=lambda s=scene: self.send_switch_scene(s),
                bg='#6a8759' if scene == self.current_scene else '#3c3f41',
                fg='white',
                relief=tk.FLAT,
                font=('Segoe UI', 9),
                padx=15,
                pady=8
            )
            btn.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
            btn.bind('<Enter>', lambda e, b=btn, s=scene: b.configure(bg='#7a9769' if s == self.current_scene else '#4a4d4f'))
            btn.bind('<Leave>', lambda e, b=btn, s=scene: b.configure(bg='#6a8759' if s == self.current_scene else '#3c3f41'))

    def load_settings(self):
        """Load groups and hidden scenes from JSON file"""
        global scene_groups  # Explicitly declare we're modifying the global
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    # Update global scene_groups
                    scene_groups.clear()  # Clear existing
                    scene_groups.update(settings.get('scene_groups', {}))
                    # Update instance hidden_scenes
                    self.hidden_scenes = settings.get('hidden_scenes', {})
                    # Convert hidden_scenes values back to sets
                    self.hidden_scenes = {k: set(v) for k, v in self.hidden_scenes.items()}
                print(f"Loaded settings: {len(scene_groups)} groups")  # Debug print
        except Exception as e:
            print(f"Error loading settings: {e}")
            scene_groups.clear()
            self.hidden_scenes = {}

    def save_settings(self):
        """Save groups and hidden scenes to JSON file"""
        try:
            settings = {
                'scene_groups': dict(scene_groups),  # Convert to regular dict
                'hidden_scenes': {k: list(v) for k, v in self.hidden_scenes.items()}  # Convert sets to lists for JSON
            }
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
            print(f"Saved settings: {len(scene_groups)} groups")  # Debug print
        except Exception as e:
            print(f"Error saving settings: {e}")

    def add_scene_group(self):
        group_name = simpledialog.askstring("New Scene Group", "Enter Group Name:")
        if group_name and group_name not in scene_groups:
            scene_groups[group_name] = {'scenes': [], 'interval': 30}
            self.update_scene_groups()
            self.save_settings()

    def update_scene_groups(self):
        left_frame = None
        for widget in self.main_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget.winfo_x() == 0:
                left_frame = widget
                break
        
        # Initialize hidden scenes for new groups
        for group_name in scene_groups:
            if group_name not in self.hidden_scenes:
                self.hidden_scenes[group_name] = set()

        # Clear existing group frames
        for widget in left_frame.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                widget.destroy()

        # Style for group frames
        style = ttk.Style()
        style.configure('Group.TLabelframe', background='#2b2b2b', padding=10)
        style.configure('Group.TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
        style.configure('ActiveGroup.TLabelframe', background='#2b2b2b', padding=10)
        style.configure('ActiveGroup.TLabelframe.Label', font=('Segoe UI', 10, 'bold'), foreground='#4CAF50')

        # Add groups to left frame
        for group_name, details in scene_groups.items():
            # Format group title with rotation time
            group_title = f"{group_name} ({details['interval']}s)"
            
            # Use different style for active groups
            is_active = group_name in self.active_rotations
            frame = ttk.LabelFrame(
                left_frame, 
                text=group_title,
                style='ActiveGroup.TLabelframe' if is_active else 'Group.TLabelframe'
            )
            frame.pack(fill=tk.X, pady=5)

            # Add a visual indicator for active groups
            if is_active:
                indicator = tk.Label(
                    frame,
                    text="● Active",
                    bg='#2b2b2b',
                    fg='#4CAF50',
                    font=('Segoe UI', 8)
                )
                indicator.pack(anchor='ne', padx=5)
            
            # Style the listbox
            listbox = tk.Listbox(
                frame,
                bg='#3c3f41',
                fg='white',
                selectmode=tk.SINGLE,
                font=('Segoe UI', 9),
                relief=tk.FLAT,
                selectbackground='#4a4d4f',
                highlightthickness=0
            )
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            for scene in details['scenes']:
                # Add "[HIDDEN] " prefix and gray color for hidden scenes
                if scene in self.hidden_scenes.get(group_name, set()):
                    listbox.insert(tk.END, f"[HIDDEN] {scene}")
                    listbox.itemconfig(tk.END, fg='#666666')  # Gray out hidden scenes
                else:
                    listbox.insert(tk.END, scene)
                    listbox.itemconfig(tk.END, fg='white')
            
            btn_frame = tk.Frame(frame, bg='#2b2b2b')
            btn_frame.pack(side=tk.RIGHT)
            
            # Create two sub-frames for better organization
            scene_btn_frame = tk.Frame(btn_frame, bg='#2b2b2b')
            scene_btn_frame.pack(side=tk.TOP, pady=(0, 10))
            
            group_btn_frame = tk.Frame(btn_frame, bg='#2b2b2b')
            group_btn_frame.pack(side=tk.BOTTOM)
            
            # Scene management buttons (top frame)
            scene_buttons = [
                ('Add', lambda g=group_name: self.add_scene_to_group(g)),
                ('Remove', lambda g=group_name, lb=listbox: self.remove_scene_from_group(g, lb)),
                ('Toggle Hide', lambda: self.toggle_hide(group_name, listbox))
            ]
            
            # Group management buttons (bottom frame)
            group_buttons = [
                ('Edit Time', lambda g=group_name: self.edit_group_time(g)),
                ('Delete', lambda g=group_name: self.delete_scene_group(g))
            ]
            
            # Add Start/Stop button separately for prominence
            start_stop_btn = tk.Button(
                scene_btn_frame,
                text="Stop" if is_active else "Start",
                command=lambda g=group_name, b=None: self.toggle_scene_cycle(g, b),
                bg='#4CAF50',
                fg='white',
                relief=tk.FLAT,
                font=('Segoe UI', 9, 'bold'),
                width=8,
                pady=4
            )
            start_stop_btn.pack(pady=(0, 5))
            start_stop_btn.configure(command=lambda g=group_name, b=start_stop_btn: self.toggle_scene_cycle(g, b))
            
            # Hover effects for start/stop button
            current_color = '#4CAF50'
            start_stop_btn.bind('<Enter>', lambda e, b=start_stop_btn: b.configure(bg=self.adjust_color(current_color, -20)))
            start_stop_btn.bind('<Leave>', lambda e, b=start_stop_btn: b.configure(bg=current_color))
            
            # Create scene management buttons
            for text, cmd in scene_buttons:
                btn = tk.Button(
                    scene_btn_frame,
                    text=text,
                    command=cmd,
                    bg='#4CAF50',
                    fg='white',
                    relief=tk.FLAT,
                    font=('Segoe UI', 9),
                    width=8,
                    pady=4
                )
                btn.pack(pady=2)
                btn.bind('<Enter>', lambda e, b=btn: b.configure(bg=self.adjust_color('#4CAF50', -20)))
                btn.bind('<Leave>', lambda e, b=btn: b.configure(bg='#4CAF50'))
            
            # Create group management buttons
            for text, cmd in group_buttons:
                btn = tk.Button(
                    group_btn_frame,
                    text=text,
                    command=cmd,
                    bg='#4CAF50',
                    fg='white',
                    relief=tk.FLAT,
                    font=('Segoe UI', 9),
                    width=8,
                    pady=4
                )
                btn.pack(pady=2)
                btn.bind('<Enter>', lambda e, b=btn: b.configure(bg=self.adjust_color('#4CAF50', -20)))
                btn.bind('<Leave>', lambda e, b=btn: b.configure(bg='#4CAF50'))

    def toggle_scene_cycle(self, group_name, button):
        if group_name in self.active_rotations:
            self.stop_scene_cycle(group_name)
            button.configure(text="Start", bg='#4CAF50')
            button.bind('<Enter>', lambda e, b=button: b.configure(bg=self.adjust_color('#4CAF50', -20)))
            button.bind('<Leave>', lambda e, b=button: b.configure(bg='#4CAF50'))
        else:
            self.start_scene_cycle(group_name)
            button.configure(text="Stop", bg='#4CAF50')
            button.bind('<Enter>', lambda e, b=button: b.configure(bg=self.adjust_color('#4CAF50', -20)))
            button.bind('<Leave>', lambda e, b=button: b.configure(bg='#4CAF50'))
        
        # Update the groups to reflect the new active state
        self.update_scene_groups()

    def add_scene_to_group(self, group_name):
        add_scene_window = tk.Toplevel(self.overlay)
        add_scene_window.title("Add Scenes to Group")
        add_scene_window.configure(bg='#2b2b2b')
        
        # Calculate available scenes
        available_scenes = [scene for scene in self.scenes 
                          if scene not in scene_groups[group_name]['scenes']]
        
        # Get screen dimensions
        screen_width = add_scene_window.winfo_screenwidth()
        screen_height = add_scene_window.winfo_screenheight()
        
        # Calculate optimal layout
        tile_width = 150  # Base tile width
        tile_height = 150  # Base tile height
        padding = 20  # Padding between tiles
        
        # Calculate number of columns based on screen width
        max_columns = min(5, (screen_width - 100) // (tile_width + padding))  # Max 5 columns
        num_columns = min(max_columns, max(2, len(available_scenes) // 2))  # At least 2 columns
        
        # Calculate rows needed
        num_rows = (len(available_scenes) + num_columns - 1) // num_columns
        
        # Calculate window dimensions
        window_width = (tile_width + padding) * num_columns + padding * 2
        window_height = (tile_height + padding) * min(num_rows, 6) + 150  # +150 for header and buttons
        
        # Ensure window isn't too large
        window_width = min(window_width, screen_width - 100)
        window_height = min(window_height, screen_height - 100)
        
        # Center window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        add_scene_window.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # Create main container with scrolling
        container = tk.Frame(add_scene_window, bg='#2b2b2b')
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title label
        tk.Label(
            container,
            text=f"Select scenes to add to '{group_name}'",
            bg='#2b2b2b',
            fg='white',
            font=('Segoe UI', 20, 'bold')
        ).pack(pady=(0, 10))
        
        # Create canvas and scrollbar for tiles
        canvas = tk.Canvas(container, bg='#2b2b2b', highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2b2b2b')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Grid for scene tiles
        row = 0
        col = 0
        selected_scenes = []
        scene_buttons = {}
        
        def toggle_scene(scene, button):
            if scene in selected_scenes:
                selected_scenes.remove(scene)
                button.configure(bg='#3c3f41')
            else:
                selected_scenes.append(scene)
                button.configure(bg='#6a8759')
        
        # Configure grid columns to be equal width
        for i in range(num_columns):
            scrollable_frame.grid_columnconfigure(i, weight=1)
        
        # Create scene tiles
        for scene in available_scenes:
            frame = tk.Frame(
                scrollable_frame,
                bg='#2b2b2b',
                padx=5,
                pady=5
            )
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            btn = tk.Button(
                frame,
                text=scene,
                bg='#3c3f41',
                fg='white',
                relief=tk.FLAT,
                font=('Segoe UI', 9),
                wraplength=tile_width - 20
            )
            btn.configure(command=lambda s=scene, b=btn: toggle_scene(s, b))
            btn.pack(expand=True, fill=tk.BOTH)
            
            # Hover effects
            btn.bind('<Enter>', lambda e, b=btn, s=scene: b.configure(
                bg='#7a9769' if s in selected_scenes else '#4a4d4f'))
            btn.bind('<Leave>', lambda e, b=btn, s=scene: b.configure(
                bg='#6a8759' if s in selected_scenes else '#3c3f41'))
            
            scene_buttons[scene] = btn
            
            col += 1
            if col >= num_columns:
                col = 0
                row += 1
        
        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Button container
        button_container = tk.Frame(add_scene_window, bg='#2b2b2b')
        button_container.pack(fill=tk.X, padx=10, pady=10)
        
        def confirm_selection():
            for scene in selected_scenes:
                if scene not in scene_groups[group_name]['scenes']:
                    scene_groups[group_name]['scenes'].append(scene)
            self.update_scene_groups()
            self.save_settings()
            add_scene_window.destroy()
        
        # Add buttons
        tk.Button(
            button_container,
            text="Add Selected",
            command=confirm_selection,
            bg='#4CAF50',
            fg='white',
            relief=tk.FLAT,
            font=('Segoe UI', 10),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_container,
            text="Cancel",
            command=add_scene_window.destroy,
            bg='#666666',
            fg='white',
            relief=tk.FLAT,
            font=('Segoe UI', 10),
            padx=20,
            pady=5
        ).pack(side=tk.LEFT, padx=5)
        
        # Clean up mousewheel binding when window closes
        def on_closing():
            canvas.unbind_all("<MouseWheel>")
            add_scene_window.destroy()
        
        add_scene_window.protocol("WM_DELETE_WINDOW", on_closing)

    def remove_scene_from_group(self, group_name, listbox):
        selected = listbox.curselection()
        if selected:
            scene = listbox.get(selected[0]).replace("[HIDDEN] ", "")  # Remove hidden prefix if present
            scene_groups[group_name]['scenes'].remove(scene)
            self.update_scene_groups()
            self.save_settings()
    
    def delete_scene_group(self, group_name):
        if group_name in self.hidden_scenes:
            del self.hidden_scenes[group_name]
        del scene_groups[group_name]
        self.update_scene_groups()
        self.save_settings()
    
    def start_scene_cycle(self, group_name):
        if group_name in self.active_rotations:
            return  # Don't start if already running
        
        self.active_rotations.add(group_name)
        
        def cycle():
            while group_name in scene_groups and group_name in self.active_rotations:
                # Filter out hidden scenes during rotation
                visible_scenes = [scene for scene in scene_groups[group_name]['scenes'] 
                                if scene not in self.hidden_scenes.get(group_name, set())]
                
                if not visible_scenes:  # Skip if all scenes are hidden
                    time.sleep(1)
                    continue
                    
                for scene in visible_scenes:
                    if group_name not in self.active_rotations:
                        break
                    self.send_switch_scene(scene)
                    time.sleep(scene_groups[group_name]['interval'])
            
            if group_name in self.active_rotations:
                self.active_rotations.remove(group_name)
        
        threading.Thread(target=cycle, daemon=True).start()

    def stop_scene_cycle(self, group_name):
        if group_name in self.active_rotations:
            self.active_rotations.remove(group_name)

    def edit_group_time(self, group_name):
        edit_window = tk.Toplevel(self.overlay)
        edit_window.title(f"Edit Rotation Time - {group_name}")
        edit_window.configure(bg='#2b2b2b')
        edit_window.grab_set()  # Make window modal
        
        # Center the window
        window_width = 300
        window_height = 150
        screen_width = edit_window.winfo_screenwidth()
        screen_height = edit_window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        edit_window.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # Current interval label
        current_time = scene_groups[group_name]['interval']
        tk.Label(
            edit_window,
            text=f"Current interval: {current_time} seconds",
            bg='#2b2b2b',
            fg='white',
            font=('Segoe UI', 10)
        ).pack(pady=10)
        
        tk.Label(
            edit_window,
            text="New interval (seconds):",
            bg='#2b2b2b',
            fg='white',
            font=('Segoe UI', 10)
        ).pack(pady=(0, 5))
        
        # Entry for new time
        time_var = tk.StringVar(value=str(current_time))
        entry = tk.Entry(
            edit_window,
            textvariable=time_var,
            bg='#3c3f41',
            fg='white',
            insertbackground='white',
            relief=tk.FLAT
        )
        entry.pack(pady=5, padx=20, fill=tk.X)
        
        def save_time():
            try:
                new_time = float(time_var.get())
                if new_time > 0:
                    scene_groups[group_name]['interval'] = new_time
                    self.save_settings()
                    edit_window.destroy()
                else:
                    tk.messagebox.showerror("Invalid Input", "Please enter a positive number")
            except ValueError:
                tk.messagebox.showerror("Invalid Input", "Please enter a valid number")
        
        # Save button
        tk.Button(
            edit_window,
            text="Save",
            command=save_time,
            bg='#4CAF50',
            fg='white',
            relief=tk.FLAT,
            padx=20
        ).pack(pady=10)

    def update_scene_highlighting(self):
        # Update highlighting in scene list and groups
        for widget in self.main_frame.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    # Update scene buttons in right frame
                    if isinstance(child, tk.Button) and child.cget('text') == self.current_scene:
                        child.configure(bg='#6a8759')  # Highlight color for active scene
                    elif isinstance(child, tk.Button):
                        child.configure(bg='#3c3f41')  # Reset other buttons
                    
                    # Update scene groups in left frame
                    if isinstance(child, ttk.LabelFrame):
                        for group_widget in child.winfo_children():
                            if isinstance(group_widget, tk.Listbox):
                                for i in range(group_widget.size()):
                                    if group_widget.get(i) == self.current_scene:
                                        group_widget.itemconfig(i, bg='#6a8759')
                                    else:
                                        group_widget.itemconfig(i, bg='#3c3f41')

    def validate_scene_groups(self):
        """Hide any scenes that don't exist in OBS from groups"""
        scenes_set = set(self.scenes)
        
        # Initialize hidden scenes for any groups that don't have them
        for group_name in scene_groups:
            if group_name not in self.hidden_scenes:
                self.hidden_scenes[group_name] = set()
        
        # Process each group
        for group_name in list(scene_groups.keys()):
            # Check each scene in the group
            for scene in scene_groups[group_name]['scenes']:
                if scene not in scenes_set:
                    print(f"Scene '{scene}' not found in OBS - hiding in group '{group_name}'")
                    self.hidden_scenes[group_name].add(scene)
            
            # Remove empty groups
            visible_scenes = [scene for scene in scene_groups[group_name]['scenes'] 
                             if scene in scenes_set]
            if not visible_scenes:
                print(f"All scenes in group '{group_name}' are hidden or invalid")
        
        # Clean up hidden scenes for non-existent groups
        for group_name in list(self.hidden_scenes.keys()):
            if group_name not in scene_groups:
                del self.hidden_scenes[group_name]
        
        # Save the updated settings
        self.save_settings()

    def toggle_hide(self, group_name, listbox):
        selected = listbox.curselection()
        if selected:
            scene_text = listbox.get(selected[0])
            scene = scene_text.replace("[HIDDEN] ", "")
            
            if scene in self.hidden_scenes[group_name]:
                self.hidden_scenes[group_name].remove(scene)
                listbox.delete(selected)
                listbox.insert(selected, scene)
                listbox.itemconfig(selected, fg='white')
            else:
                self.hidden_scenes[group_name].add(scene)
                listbox.delete(selected)
                listbox.insert(selected, f"[HIDDEN] {scene}")
                listbox.itemconfig(selected, fg='#666666')
            
            listbox.selection_set(selected)
            self.save_settings()

# Run UI
def main():
    root = tk.Tk()
    root.title("OBS Advanced Scene Switcher")
    root.geometry("500x700")  # Slightly larger default size
    
    # Set window icon (if you have one)
    # root.iconbitmap('path_to_icon.ico')
    
    # Make window resizable
    root.minsize(400, 500)
    
    app = OBSController(root)
    root.mainloop()

if __name__ == "__main__":
    main()