import os
import json
import pygame
import argparse

class FrameReviewer:
    def __init__(self, output_dir, marked_file="marked_frames.json"):
        self.output_dir = output_dir
        self.marked_file = marked_file
        self.frames = sorted([f for f in os.listdir(output_dir) if f.startswith("frame_") and f.endswith(".png")])
        self.current_index = 0
        self.marked_frames = self.load_marked_frames()

        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((800, 650))  # Increased height for the slider
        pygame.display.set_caption("Frame Reviewer")
        self.font = pygame.font.Font(None, 36)

        # Slider dimensions
        self.slider_rect = pygame.Rect(50, 10, 700, 20)  # Positioned at the top
        self.slider_knob_width = 10

        self.run()

    def load_marked_frames(self):
        if os.path.exists(self.marked_file):
            with open(self.marked_file, "r") as f:
                return set(json.load(f))
        return set()

    def save_marked_frames(self):
        with open(self.marked_file, "w") as f:
            json.dump(list(self.marked_frames), f, indent=4)

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
        scale = min(screen_width / image_width, (screen_height - 50) / image_height)  # Leave space for the slider
        new_width = int(image_width * scale)
        new_height = int(image_height * scale)
        image = pygame.transform.scale(image, (new_width, new_height))

        # Center the image on the screen
        x_offset = (screen_width - new_width) // 2
        y_offset = (screen_height - 50 - new_height) // 2 + 30  # Adjust for slider space at the top

        self.screen.fill((0, 0, 0))  # Clear the screen
        self.screen.blit(image, (x_offset, y_offset))

        frame_name = self.frames[self.current_index]
        marked_status = " [MARKED]" if frame_name in self.marked_frames else ""
        text = self.font.render(f"{frame_name}{marked_status}", True, (255, 255, 255))
        self.screen.blit(text, (20, screen_height - 40))

        # Draw the slider
        self.draw_slider()

        pygame.display.flip()

    def draw_slider(self):
        # Draw the slider bar
        pygame.draw.rect(self.screen, (200, 200, 200), self.slider_rect)

        # Calculate the knob position
        knob_x = self.slider_rect.x + int((self.current_index / (len(self.frames) - 1)) * self.slider_rect.width)
        knob_rect = pygame.Rect(knob_x - self.slider_knob_width // 2, self.slider_rect.y, self.slider_knob_width, self.slider_rect.height)

        # Draw the knob
        pygame.draw.rect(self.screen, (255, 0, 0), knob_rect)

    def handle_slider_click(self, mouse_x):
        # Calculate the new frame index based on the mouse click position
        if self.slider_rect.collidepoint(mouse_x, self.slider_rect.y):
            relative_x = mouse_x - self.slider_rect.x
            new_index = int((relative_x / self.slider_rect.width) * (len(self.frames) - 1))
            self.current_index = max(0, min(new_index, len(self.frames) - 1))

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
                    elif event.key == pygame.K_m:  # Jump to next marked frame
                        self.next_marked_frame()
                    elif event.key == pygame.K_n:  # Jump to previous marked frame
                        self.prev_marked_frame()
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        self.handle_slider_click(event.pos[0])
        self.save_marked_frames()
        pygame.quit()

    def prev_frame(self):
        if self.current_index > 0:
            self.current_index -= 1

    def next_frame(self):
        if self.current_index < len(self.frames) - 1:
            self.current_index += 1

    def toggle_mark(self):
        frame_name = self.frames[self.current_index]
        if frame_name in self.marked_frames:
            self.marked_frames.remove(frame_name)
        else:
            self.marked_frames.add(frame_name)

    def next_marked_frame(self):
        """Jump to the next marked frame."""
        for i in range(self.current_index + 1, len(self.frames)):
            if self.frames[i] in self.marked_frames:
                self.current_index = i
                return
        print("No next marked frame found.")

    def prev_marked_frame(self):
        """Jump to the previous marked frame."""
        for i in range(self.current_index - 1, -1, -1):
            if self.frames[i] in self.marked_frames:
                self.current_index = i
                return
        print("No previous marked frame found.")

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
