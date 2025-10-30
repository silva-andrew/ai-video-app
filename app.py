from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
import os
from datetime import datetime

app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

# Create directories
SCRIPTS_DIR = 'scripts'
VIDEOS_DIR = 'videos'
os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-script', methods=['POST'])
def generate_script():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        style = data.get('style', 'educational')
        
        if not prompt or len(prompt) > 500:
            return jsonify({'success': False, 'error': 'Prompt too long (max 500 characters)'}), 400
        
        style_prompts = {
            'educational': 'You are a professional educational content writer.',
            'marketing': 'You are an expert marketing copywriter.',
            'social_media': 'You are a viral social media content creator.'
        }
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        full_prompt = f"{style_prompts.get(style, style_prompts['educational'])} Write a short video script about: {prompt}. Keep it to 2-3 sentences, suitable for a 30-60 second video."
        
        response = model.generate_content(full_prompt)
        script_text = response.text
        
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
    try:
        import subprocess
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(VIDEOS_DIR, f'video_{timestamp}.mp4')
        
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=640x480:d=8',
            '-pix_fmt', 'yuv420p', '-y', output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=20)
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            return jsonify({
                'success': True,
                'video_url': f'/download-video/{os.path.basename(output_file)}',
                'filename': os.path.basename(output_file)
            })
        else:
            return jsonify({'success': False, 'error': 'Could not create video'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download-video/<filename>')
def download_video(filename):
    if not filename.startswith('video_') or '..' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
        return send_file(
            video_path,
            as_attachment=False,
            mimetype='video/mp4'
        )
    return jsonify({'error': 'Video not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
