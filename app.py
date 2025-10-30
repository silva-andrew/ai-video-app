from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
import os
from datetime import datetime

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
        model = genai.GenerativeModel('gemini-pro')
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
    """Generate simple video from script"""
    try:
        data = request.get_json()
        script = data.get('script', '')
        
        # Create a simple video (optimized for free hosting)
        width, height = 1280, 720
        duration = 10
        
        # Create background
        background = ColorClip(size=(width, height), color='black', duration=duration)
        
        # Create text clip
        text_clip = TextClip(
            script[:150],  # Limit text
            fontsize=40,
            color='white',
            size=(width-100, None),
            method='caption',
            align='center'
        )
        text_clip = text_clip.set_position('center').set_duration(duration)
        
        # Composite video
        final_video = CompositeVideoClip([background, text_clip])
        
        # Save video with fast encoding
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(VIDEOS_DIR, f'video_{timestamp}.mp4')
        
        final_video.write_videofile(
            output_file,
            fps=24,
            codec='libx264',
            audio=False,
            preset='ultrafast',
            verbose=False,
            logger=None
        )
        
        return jsonify({
            'success': True,
            'video_url': f'/download-video/{os.path.basename(output_file)}',
            'filename': os.path.basename(output_file)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Video error: {str(e)}'}), 500

@app.route('/download-video/<filename>')
def download_video(filename):
    """Serve video file for download"""
    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=True)
    return jsonify({'error': 'Video not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
