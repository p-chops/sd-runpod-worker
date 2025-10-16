import os
import json
import pygame
import argparse
from datetime import datetime
import csv
import hashlib
import shutil  # Import shutil for moving files

class FrameReviewer:
    def __init__(self, output_dir, cache_dir, marked_file="marked_frames.json", scene=None, scenes_csv=None):
        self.output_dir = output_dir
        self.cache_dir = cache_dir
        self.marked_file = marked_file
        self.scene = scene
        self.frames = self.load_frames(scene, scenes_csv)
        self.current_index = 0
        self.marked_frames = self.load_marked_frames()

        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((800, 700))  # Increased height for dropdown
        pygame.display.set_caption("Frame Reviewer")
        self.font = pygame.font.Font(None, 36)

        # Dropdown for annotation mode
        self.modes = ["Unmarked Frames", "All Frames", "Marked Frames"]
        self.current_mode = 0  # Default to "Unmarked Frames"

        # Slider dimensions
        self.slider_rect = pygame.Rect(50, 10, 700, 20)  # Positioned at the top
        self.slider_knob_width = 10

        self.run()

    def load_frames(self, scene, scenes_csv):
        """Load frames for the specified scene from scenes.csv."""
        if not scene or not scenes_csv:
            # Load all frames if no scene is specified
            return sorted([f for f in os.listdir(self.output_dir) if f.startswith("frame_") and f.endswith(".png")])

        # Parse scenes.csv to find the frame range for the specified scene
        with open(scenes_csv, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            scenes = {row['name']: (int(row['frame']), None) for row in reader}

        # Update end frame for each scene
        scene_names = list(scenes.keys())
        for i, name in enumerate(scene_names[:-1]):
            scenes[name] = (scenes[name][0], scenes[scene_names[i + 1]][0] - 1)
        scenes[scene_names[-1]] = (scenes[scene_names[-1]][0], None)  # Last scene goes to the end

        if scene not in scenes:
            raise ValueError(f"Scene '{scene}' not found in {scenes_csv}.")

        start_frame, end_frame = scenes[scene]
        end_frame = end_frame or float('inf')  # If no end frame, go to infinity
        return [
            f for f in sorted(os.listdir(self.output_dir))
            if f.startswith("frame_") and f.endswith(".png") and start_frame <= int(f[6:11]) <= end_frame
        ]

    def load_marked_frames(self):
        if os.path.exists(self.marked_file):
            with open(self.marked_file, "r") as f:
                return json.load(f)
        return {}

    def save_marked_frames(self):
        with open(self.marked_file, "w") as f:
            json.dump(self.marked_frames, f, indent=4)

    def compute_checksum(self, file_path):
        """Compute the SHA256 checksum of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def decache_frame(self, frame_number, trash_dir):
        """Decache a specific frame by moving it to the trash directory and removing it from the output."""
        output_frame_path = os.path.join(self.output_dir, f"frame_{frame_number:05d}.png")
        if not os.path.exists(output_frame_path):
            print(f"Output frame not found: {output_frame_path}")
            return False

        output_checksum = self.compute_checksum(output_frame_path)
        cached_files = [
            f for f in os.listdir(self.cache_dir)
            if f.startswith(f"frame_{frame_number:05d}_")
        ]

        for cached_file in cached_files:
            cached_file_path = os.path.join(self.cache_dir, cached_file)
            cached_checksum = self.compute_checksum(cached_file_path)
            if cached_checksum == output_checksum:
                # Move cached file to the trash directory
                os.makedirs(trash_dir, exist_ok=True)
                trash_path = os.path.join(trash_dir, cached_file)
                shutil.move(cached_file_path, trash_path)
                print(f"Moved cached file to trash: {trash_path}")

                # Remove the output frame
                trash_output_path = os.path.join(trash_dir, os.path.basename(output_frame_path))
                shutil.move(output_frame_path, trash_output_path)
                print(f"Moved output frame to trash: {trash_output_path}")
                return True
        print(f"No matching cached frame found for frame {frame_number}")
        return False

    def decache_marked_frames(self, trash_dir):
        """Decache all marked frames in the current scene and exit the application."""
        filtered_frames = self.get_filtered_frames()
        for frame_name in filtered_frames:
            frame_number = int(frame_name[6:11])  # Extract frame number from filename
            self.decache_frame(frame_number, trash_dir)
        print("Decached all marked frames in the current scene.")
        print("Exiting application after decaching.")
        self.save_marked_frames()
        pygame.quit()
        exit(0)  # Exit the application after decaching

    def display_frame(self):
        if not self.frames:
            self.screen.fill((0, 0, 0))
            text = self.font.render("No frames found in the output directory.", True, (255, 255, 255))
            self.screen.blit(text, (20, 20))
            pygame.display.flip()
            return

        frame_path = os.path.join(self.output_dir, self.frames[self.current_index])
        image = pygame.image.load(frame_path)

        # Scale the image while preserving aspect ratio
        image_width, image_height = image.get_size()
        screen_width, screen_height = self.screen.get_size()
        scale = min(screen_width / image_width, (screen_height - 100) / image_height)  # Leave space for dropdown and slider
        new_width = int(image_width * scale)
        new_height = int(image_height * scale)
        image = pygame.transform.scale(image, (new_width, new_height))

        # Center the image on the screen
        x_offset = (screen_width - new_width) // 2
        y_offset = (screen_height - 100 - new_height) // 2 + 50  # Adjust for dropdown and slider space

        self.screen.fill((0, 0, 0))  # Clear the screen
        self.screen.blit(image, (x_offset, y_offset))

        frame_name = self.frames[self.current_index]
        marked_status = " [MARKED]" if frame_name in self.marked_frames else ""
        text = self.font.render(f"{frame_name}{marked_status}", True, (255, 255, 255))
        self.screen.blit(text, (20, screen_height - 40))

        # Draw the slider and dropdown
        self.draw_slider()
        self.draw_dropdown()

        pygame.display.flip()

    def draw_slider(self):
        # Draw the slider bar
        pygame.draw.rect(self.screen, (200, 200, 200), self.slider_rect)

        # Calculate the knob position
        knob_x = self.slider_rect.x + int((self.current_index / (len(self.frames) - 1)) * self.slider_rect.width)
        knob_rect = pygame.Rect(knob_x - self.slider_knob_width // 2, self.slider_rect.y, self.slider_knob_width, self.slider_rect.height)

        # Draw the knob
        pygame.draw.rect(self.screen, (255, 0, 0), knob_rect)

    def draw_dropdown(self):
        # Draw the dropdown background
        dropdown_rect = pygame.Rect(50, 40, 700, 40)
        pygame.draw.rect(self.screen, (50, 50, 50), dropdown_rect)

        # Draw the current mode text
        mode_text = self.font.render(f"Mode: {self.modes[self.current_mode]}", True, (255, 255, 255))
        self.screen.blit(mode_text, (60, 50))

    def handle_click(self, mouse_x, mouse_y):
        """Handle clicks and delegate to the appropriate control based on the click position."""
        if self.slider_rect.collidepoint(mouse_x, mouse_y):
            self.handle_slider_click(mouse_x, mouse_y)
        elif 40 <= mouse_y <= 80:  # Dropdown area
            self.handle_dropdown_click(mouse_y)

    def handle_slider_click(self, mouse_x, mouse_y):
        """Handle clicks on the slider and update the current index based on the selected mode."""
        print(f"Slider clicked at x={mouse_x}, y={mouse_y}")  # Debug: Log the slider click position
        relative_x = mouse_x - self.slider_rect.x
        filtered_frames = self.get_filtered_frames()
        if filtered_frames:
            # Calculate the new index in the filtered frames
            new_filtered_index = int((relative_x / self.slider_rect.width) * (len(filtered_frames) - 1))
            new_filtered_index = max(0, min(new_filtered_index, len(filtered_frames) - 1))
            # Map the filtered index back to the full frame list
            self.current_index = self.frames.index(filtered_frames[new_filtered_index])
            print(f"Slider updated: Jumped to frame {self.frames[self.current_index]}")  # Debug: Log the new frame
            self.display_frame()  # Trigger a frame update after changing the index

    def handle_dropdown_click(self, mouse_y):
        """Handle clicks on the dropdown to cycle through modes."""
        print(f"Dropdown clicked at y={mouse_y}")  # Debug: Log the dropdown click
        self.current_mode = (self.current_mode + 1) % len(self.modes)
        print(f"Mode changed to: {self.modes[self.current_mode]}")  # Debug: Log the new mode
        self.display_frame()  # Refresh the display to reflect the new mode

    def get_filtered_frames(self):
        """Return the list of frames based on the current mode."""
        if self.modes[self.current_mode] == "All Frames":
            return self.frames
        elif self.modes[self.current_mode] == "Unmarked Frames":
            return [f for f in self.frames if f not in self.marked_frames]
        elif self.modes[self.current_mode] == "Marked Frames":
            return [f for f in self.frames if f in self.marked_frames]

    def run(self):
        running = True
        while running:
            self.display_frame()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.prev_frame()
                    elif event.key == pygame.K_RIGHT:
                        self.next_frame()
                    elif event.key == pygame.K_SPACE:
                        self.toggle_mark()
                    elif event.key == pygame.K_d:  # Hotkey for decaching marked frames
                        trash_dir = os.path.join(self.output_dir, "trash")  # Default trash directory
                        self.decache_marked_frames(trash_dir)
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    print(f"Mouse button clicked at position {event.pos}")  # Debug: Log mouse click position
                    if event.button == 1:  # Left mouse button
                        self.handle_click(event.pos[0], event.pos[1])
        self.save_marked_frames()
        pygame.quit()

    def prev_frame(self):
        """Navigate to the previous frame based on the current mode."""
        filtered_frames = self.get_filtered_frames()
        current_frame = self.frames[self.current_index]
        if current_frame in filtered_frames:
            current_filtered_index = filtered_frames.index(current_frame)
            if current_filtered_index > 0:
                self.current_index = self.frames.index(filtered_frames[current_filtered_index - 1])
        else:
            # If the current frame is not in the filtered list, jump to the last frame in the filtered list
            if filtered_frames:
                self.current_index = self.frames.index(filtered_frames[-1])

    def next_frame(self):
        """Navigate to the next frame based on the current mode."""
        filtered_frames = self.get_filtered_frames()
        current_frame = self.frames[self.current_index]
        if current_frame in filtered_frames:
            current_filtered_index = filtered_frames.index(current_frame)
            if current_filtered_index < len(filtered_frames) - 1:
                self.current_index = self.frames.index(filtered_frames[current_filtered_index + 1])
        else:
            # If the current frame is not in the filtered list, jump to the first frame in the filtered list
            if filtered_frames:
                self.current_index = self.frames.index(filtered_frames[0])

    def toggle_mark(self):
        frame_name = self.frames[self.current_index]
        if frame_name in self.marked_frames:
            del self.marked_frames[frame_name]
        else:
            self.marked_frames[frame_name] = datetime.now().isoformat()

def main():
    parser = argparse.ArgumentParser(description="Review and mark frames for decaching.")
    parser.add_argument("output_dir", help="Directory containing output frames.")
    parser.add_argument("--cache-dir", default=".img2img_cache", help="Directory containing cached frames (default: .img2img_cache).")
    parser.add_argument("--marked-file", default="marked_frames.json", help="File to save marked frames (default: marked_frames.json).")
    parser.add_argument("--scene", help="Name of the scene to work on (optional).")
    parser.add_argument("--scenes-csv", default="./scenes.csv", help="Path to scenes.csv file (required if --scene is specified).")
    parser.add_argument("--trash-dir", default="./trash", help="Directory to move decached files to (default: ./trash).")
    args = parser.parse_args()

    if not os.path.isdir(args.output_dir):
        print(f"Error: {args.output_dir} is not a valid directory.")
        return

    # Ensure the cache directory exists
    if not os.path.isdir(args.cache_dir):
        print(f"Error: Cache directory '{args.cache_dir}' does not exist.")
        return

    if args.scene and not os.path.exists(args.scenes_csv):
        print(f"Error: scenes.csv file not found at {args.scenes_csv}.")
        return

    FrameReviewer(args.output_dir, args.cache_dir, args.marked_file, args.scene, args.scenes_csv)

if __name__ == "__main__":
    main()
