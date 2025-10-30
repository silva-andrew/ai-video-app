from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
import os
from datetime import datetime
import os
os.environ['TMPDIR'] = '/tmp'  # Use persistent temp directory


app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

# Create directories for storing files
SCRIPTS_DIR = 'scripts'
VIDEOS_DIR = 'videos'
os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/generate-script', methods=['POST'])
def generate_script():
    """Generate video script using Gemini API"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        style = data.get('style', 'educational')
        
        if not prompt or len(prompt) > 500:
            return jsonify({'success': False, 'error': 'Prompt too long (max 500 characters)'}), 400
        
        # Create style-specific prompts
        style_prompts = {
            'educational': 'You are a professional educational content writer. Write engaging, informative content.',
            'marketing': 'You are an expert marketing copywriter. Write persuasive, compelling copy.',
            'social_media': 'You are a viral social media content creator. Write trendy, engaging content.'
        }
        
        # Use Gemini API to generate script
        model = genai.GenerativeModel('gemini-2.5-flash')
        full_prompt = f"{style_prompts.get(style, style_prompts['educational'])} Write a short video script about: {prompt}. Keep it to 2-3 sentences, suitable for a 30-60 second video."
        
        response = model.generate_content(full_prompt)
        script_text = response.text
        
        # Save script to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        script_file = os.path.join(SCRIPTS_DIR, f'script_{timestamp}.txt')
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(script_text)
        
        return jsonify({
            'success': True,
            'script': script_text,
            'word_count': len(script_text.split()),
            'estimated_duration': max(10, len(script_text.split()) / 3)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500

@app.route('/generate-video', methods=['POST'])
def generate_video():
    """Generate video using pure Python (no FFmpeg needed)"""
    try:
        data = request.get_json()
        script = data.get('script', '')
        
        # Create video using PIL/imageio (no FFmpeg needed)
        import imageio
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(VIDEOS_DIR, f'video_{timestamp}.mp4')
        
        # Create frames
        frames = []
        width, height = 640, 480
        duration = 8
        fps = 12
        total_frames = duration * fps
        
        # Create image with text
        img = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Add text to image
        text = script[:80]  # Limit text
        draw.text((50, 200), text, fill=(255, 255, 255))
        
        # Convert to numpy array
        frame = np.array(img)
        
        # Repeat frame for duration
        for _ in range(total_frames):
            frames.append(frame)
        
        # Write video
        imageio.mimwrite(output_file, frames, fps=fps, codec='libx264')
        
        if os.path.exists(output_file):
    file_size = os.path.getsize(output_file)
    if file_size > 1000:  # At least 1KB
        return jsonify({
            'success': True,
            'video_url': f'/download-video/{os.path.basename(output_file)}',
            'filename': os.path.basename(output_file),
            'size': file_size
        })
    else:
        return jsonify({'success': False, 'error': 'Video file too small'}), 500

        else:
            return jsonify({'success': False, 'error': 'Video not created'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/download-video/<filename>')
def download_video(filename):
    """Serve video file for download"""
    # Security: only allow filenames starting with 'video_'
    if not filename.startswith('video_') or '..' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
        return send_file(
            video_path,
            as_attachment=False,  # Display in browser instead of download
            mimetype='video/mp4'
        )
    return jsonify({'error': 'Video not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
