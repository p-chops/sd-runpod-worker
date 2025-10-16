import os
import json
import pygame
import argparse
from datetime import datetime

class FrameReviewer:
    def __init__(self, output_dir, marked_file="marked_frames.json"):
        self.output_dir = output_dir
        self.marked_file = marked_file
        self.frames = sorted([f for f in os.listdir(output_dir) if f.startswith("frame_") and f.endswith(".png")])
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

    def load_marked_frames(self):
        if os.path.exists(self.marked_file):
            with open(self.marked_file, "r") as f:
                return json.load(f)
        return {}

    def save_marked_frames(self):
        with open(self.marked_file, "w") as f:
            json.dump(self.marked_frames, f, indent=4)

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
    parser.add_argument("--marked-file", default="marked_frames.json", help="File to save marked frames (default: marked_frames.json).")
    args = parser.parse_args()

    if not os.path.isdir(args.output_dir):
        print(f"Error: {args.output_dir} is not a valid directory.")
        return

    FrameReviewer(args.output_dir, args.marked_file)

if __name__ == "__main__":
    main()
