import json
import time
import uuid
import threading
import websocket
import tkinter as tk
import ctypes
from tkinter import ttk, simpledialog

# OBS WebSocket Config
OBS_HOST = "ws://IP:Port"  # Change to the IP and port of the OBS WebSocket server
PASSWORD = "Password"  # Your OBS WebSocket password

# Global Variables
scene_groups = {}
ws = None

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
        self.connect()

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

    def populate_scene_buttons(self):
        for widget in self.overlay.winfo_children():
            widget.destroy()
        
        add_group_btn = tk.Button(self.overlay, text="+", command=self.add_scene_group)
        add_group_btn.pack(side=tk.TOP, anchor=tk.W, padx=5, pady=5)
        
        for scene in self.scenes:
            btn = tk.Button(self.overlay, text=scene, command=lambda s=scene: self.send_switch_scene(s))
            btn.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

    def add_scene_group(self):
        group_name = simpledialog.askstring("New Scene Group", "Enter Group Name:")
        if group_name and group_name not in scene_groups:
            scene_groups[group_name] = {'scenes': [], 'interval': 30}
            self.update_scene_groups()

    def update_scene_groups(self):
        for widget in self.overlay.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                widget.destroy()

        for group_name, details in scene_groups.items():
            frame = ttk.LabelFrame(self.overlay, text=group_name)
            frame.pack(fill=tk.X, padx=5, pady=5)
            
            listbox = tk.Listbox(frame)
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            for scene in details['scenes']:
                listbox.insert(tk.END, scene)
            
            btn_frame = tk.Frame(frame)
            btn_frame.pack(side=tk.RIGHT)
            
            tk.Button(btn_frame, text="Add", command=lambda g=group_name: self.add_scene_to_group(g)).pack(fill=tk.X)
            tk.Button(btn_frame, text="Remove", command=lambda g=group_name, lb=listbox: self.remove_scene_from_group(g, lb)).pack(fill=tk.X)
            tk.Button(btn_frame, text="Delete", command=lambda g=group_name: self.delete_scene_group(g)).pack(fill=tk.X)
            tk.Button(btn_frame, text="Start", command=lambda g=group_name: self.start_scene_cycle(g)).pack(fill=tk.X)
            
    def add_scene_to_group(self, group_name):
        add_scene_window = tk.Toplevel(self.overlay)
        add_scene_window.title("Add Scene")
        
        tk.Label(add_scene_window, text="Select Scene:").pack()
        scene_var = tk.StringVar()
        scene_dropdown = ttk.Combobox(add_scene_window, textvariable=scene_var, values=self.scenes)
        scene_dropdown.pack()
        
        def confirm_selection():
            scene = scene_var.get()
            if scene and scene not in scene_groups[group_name]['scenes']:
                scene_groups[group_name]['scenes'].append(scene)
                self.update_scene_groups()
            add_scene_window.destroy()
        
        tk.Button(add_scene_window, text="Add", command=confirm_selection).pack()
    
    def remove_scene_from_group(self, group_name, listbox):
        selected = listbox.curselection()
        if selected:
            scene = listbox.get(selected[0])
            scene_groups[group_name]['scenes'].remove(scene)
            self.update_scene_groups()
    
    def delete_scene_group(self, group_name):
        del scene_groups[group_name]
        self.update_scene_groups()
    
    def start_scene_cycle(self, group_name):
        def cycle():
            while group_name in scene_groups:
                for scene in scene_groups[group_name]['scenes']:
                    self.send_switch_scene(scene)
                    time.sleep(scene_groups[group_name]['interval'])
        threading.Thread(target=cycle, daemon=True).start()

# Run UI
def main():
    root = tk.Tk()
    root.title("OBS Advanced Scene Switcher")
    root.geometry("400x600")
    app = OBSController(root)
    root.mainloop()

if __name__ == "__main__":
    main()