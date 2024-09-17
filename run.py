import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import glob

class TimeLapseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Time Lapse Camera Setup")
        self.create_widgets()
        self.detect_cameras()

    def create_widgets(self):
        # Camera Selection
        self.camera_label = ttk.Label(self.root, text="Select Camera:")
        self.camera_label.pack(pady=5)
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(self.root, textvariable=self.camera_var)
        self.camera_combo.pack(pady=5)

        # Interval Selection
        self.interval_label = ttk.Label(self.root, text="Interval between pictures (in seconds):")
        self.interval_label.pack(pady=5)
        self.interval_var = tk.StringVar(value="60")
        self.interval_entry = ttk.Entry(self.root, textvariable=self.interval_var)
        self.interval_entry.pack(pady=5)

        # Picture Quality Selection
        self.quality_label = ttk.Label(self.root, text="Select Picture Quality:")
        self.quality_label.pack(pady=5)
        self.quality_var = tk.StringVar()
        self.quality_combo = ttk.Combobox(self.root, textvariable=self.quality_var)
        self.quality_combo['values'] = ('Low', 'Medium', 'High')
        self.quality_combo.current(1)
        self.quality_combo.pack(pady=5)

        # Directory Selection
        self.dir_label = ttk.Label(self.root, text="Select Directory to Save Images:")
        self.dir_label.pack(pady=5)
        self.dir_var = tk.StringVar()
        self.dir_entry = ttk.Entry(self.root, textvariable=self.dir_var, width=40)
        self.dir_entry.pack(pady=5)
        self.dir_button = ttk.Button(self.root, text="Browse", command=self.select_directory)
        self.dir_button.pack(pady=5)

        # Apply Button
        self.apply_button = ttk.Button(self.root, text="Apply Settings", command=self.apply_settings)
        self.apply_button.pack(pady=20)

    def detect_cameras(self):
        cameras = []
        video_devices = glob.glob('/dev/video*')
        for device in video_devices:
            cameras.append(device)
        if not cameras:
            messagebox.showerror("Error", "No cameras detected.")
            self.root.quit()
        self.camera_combo['values'] = cameras
        self.camera_combo.current(0)

    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_var.set(directory)

    def apply_settings(self):
        camera = self.camera_var.get()
        interval = self.interval_var.get()
        quality = self.quality_var.get()
        directory = self.dir_var.get()

        # Input Validation
        if not camera or not interval or not quality or not directory:
            messagebox.showerror("Error", "All fields are required.")
            return

        if not interval.isdigit() or int(interval) <= 0:
            messagebox.showerror("Error", "Interval must be a positive integer.")
            return

        if not os.path.isdir(directory):
            messagebox.showerror("Error", "The selected directory does not exist.")
            return

        # Clean up old cron jobs
        self.cleanup_cronjobs()

        # Set up new cron jobs
        self.setup_cronjobs(camera, interval, quality, directory)

        messagebox.showinfo("Success", "Settings applied successfully.")

    def cleanup_cronjobs(self):
        try:
            cron_output = subprocess.check_output(['crontab', '-l'], universal_newlines=True)
        except subprocess.CalledProcessError:
            cron_output = ''
        cron_lines = cron_output.strip().split('\n')
        new_cron_lines = [line for line in cron_lines if '#timelapse' not in line]
        cron_text = '\n'.join(new_cron_lines) + '\n'
        subprocess.run(['crontab', '-'], input=cron_text, text=True)

    def setup_cronjobs(self, camera, interval, quality, directory):
        # Create capture script
        capture_script = os.path.expanduser('~/capture_image.sh')
        with open(capture_script, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write(f'DIR="{directory}"\n')
            f.write('DATE=$(date +"%Y%m%d_%H%M%S")\n')
            quality_settings = {
                'Low': '--resolution 640x480',
                'Medium': '--resolution 1280x720',
                'High': '--resolution 1920x1080'
            }
            f.write(f'fswebcam {quality_settings[quality]} -d {camera} "$DIR/image_$DATE.jpg"\n')
        os.chmod(capture_script, 0o755)

        # Create time-lapse script
        timelapse_script = os.path.expanduser('~/create_timelapse.sh')
        with open(timelapse_script, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write(f'DIR="{directory}"\n')
            f.write('cd "$DIR"\n')
            f.write('ffmpeg -y -pattern_type glob -i "image_*.jpg" -c:v libx264 -vf fps=25 -pix_fmt yuv420p timelapse.mp4\n')
        os.chmod(timelapse_script, 0o755)

        # Set up cron jobs
        cron_jobs = f"*/{interval} * * * * {capture_script} #timelapse\n"
        cron_jobs += f"0 0 * * * {timelapse_script} #timelapse\n"
        subprocess.run(['crontab', '-'], input=cron_jobs, text=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = TimeLapseApp(root)
    root.mainloop()

