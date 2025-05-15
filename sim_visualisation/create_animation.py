def create_animation_from_frames(prefix, domain_name, fps=10):
    """
    Create an mp4 animation from the saved frames.

    Args:
        prefix: Directory containing the frames
        domain_name: Name of the domain (used in filenames)
        fps: Frames per second
    """
    try:
        import subprocess
        import glob

        # Find all frame files
        frame_pattern = f"{prefix}{domain_name}_fig_*.png"
        frames = sorted(glob.glob(frame_pattern))

        if not frames:
            print("No frames found to create animation")
            return False

        print(f"Creating animation from {len(frames)} frames...")

        # Create animation using ffmpeg
        output_file = f"{prefix}{domain_name}_animation.mp4"

        # Construct ffmpeg command
        cmd = [
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-pattern_type', 'glob',
            '-i', frame_pattern,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',  # Ensure even dimensions
            output_file
        ]

        # Run the command
        subprocess.run(cmd, check=True)
        print(f"Animation created: {output_file}")
        return True

    except ImportError:
        print("Could not create animation: ffmpeg might not be installed or accessible")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error creating animation: {e}")
        return False


if __name__ == "__main__":
    create_animation_from_frames("../cromosim_micro_social_json_sim/results/", "room", fps=5)
