import asyncio
import os
import json
import re
import requests
from google import genai
from google.genai import types
# Using MoviePy v2.0 safe imports
from moviepy import AudioFileClip, VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
import edge_tts

# Clean up raw AI string responses
def clean_json_string(raw_text: str) -> str:
    cleaned = raw_text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

# Step 1: Ask Gemini for the video plan
def generate_video_blueprint(topic: str, api_key: str):
    client = genai.Client(api_key=api_key)
    prompt = f"""
    Create a premium YouTube video script blueprint for the topic: "{topic}".
    The video must have exactly 3 consecutive scenes.
    Keep the narration concise (around 10-15 words per scene).
    
    You MUST return your response strictly as a JSON object matching this schema layout:
    {{
        "scenes": [
            {{
                "scene_number": 1,
                "narration_text": "Clean spoken narration text for this specific scene.",
                "media_search_keyword": "one single clear stock video search term"
            }}
        ]
    }}
    Do not wrap the JSON in markdown code blocks. Return raw JSON text only.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(clean_json_string(response.text))

# Step 2: Fetch Stock Footage
def fetch_pexels_video(keyword: str, api_key: str, scene_num: int) -> str:
    headers = {"Authorization": api_key}
    url = f"[https://api.pexels.com/videos/search?query=](https://api.pexels.com/videos/search?query=){keyword}&per_page=1&orientation=landscape"
    
    try:
        response = requests.get(url, headers=headers, timeout=15).json()
        if not response.get('videos'):
            fallback_url = f"[https://api.pexels.com/videos/search?query=cinematic&per_page=1&orientation=landscape](https://api.pexels.com/videos/search?query=cinematic&per_page=1&orientation=landscape)"
            response = requests.get(fallback_url, headers=headers, timeout=15).json()

        video_url = response['videos'][0]['video_files'][0]['link']
        filename = f"scene_{scene_num}.mp4"
        
        with open(filename, 'wb') as f:
            f.write(requests.get(video_url, timeout=30).content)
        return filename
    except Exception as e:
        print(f"⚠️ Video skip for Scene {scene_num}: {e}")
        return None

# Step 3: Run the Orchestration Pipeline
async def generate_final_video(topic: str, gemini_key: str, pexels_key: str, voice: str):
    blueprint = generate_video_blueprint(topic, gemini_key)
    video_segments = []
    temp_files = []
    
    for scene in blueprint.get('scenes', []):
        num = scene['scene_number']
        text = scene['narration_text']
        keyword = scene['media_search_keyword']
        
        audio_path = f"audio_{num}.mp3"
        temp_files.append(audio_path)
        
        try:
            # Generate premium TTS voiceover track
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(audio_path)
            
            # Download stock visual clip assets
            video_path = fetch_pexels_video(keyword, pexels_key, num)
            
            if video_path:
                temp_files.append(video_path)
                
                audio_clip = AudioFileClip(audio_path)
                raw_video = VideoFileClip(video_path)
                
                # Match timing perfectly
                if raw_video.duration > audio_clip.duration:
                    timed_video = raw_video.subclipped(0, audio_clip.duration)
                else:
                    timed_video = raw_video.with_duration(audio_clip.duration)
                
                # Add professional subtitle captions to the clip segment
                caption_clip = (TextClip(text=text, 
                                         font_size=32, 
                                         color='white', 
                                         size=(timed_video.width - 100, None),
                                         method='caption')
                                .with_duration(audio_clip.duration)
                                .with_position(('center', 'bottom')))
                
                # Composite the text track cleanly above the video array
                scened_video = CompositeVideoClip([timed_video, caption_clip]).with_audio(audio_clip)
                video_segments.append(scened_video)
                
        except Exception as scene_error:
            print(f"❌ Error compiling scene {num}: {scene_error}")
            continue

    if video_segments:
        output_name = "premium_output_video.mp4"
        final_render = concatenate_videoclips(video_segments, method="compose")
        final_render.write_videofile(output_name, fps=24, codec="libx264", audio_codec="aac")
        
        # Memory overhead cleanup management
        final_render.close()
        for segment in video_segments:
            segment.close()
            
        # Clean up files completely
        for file in temp_files:
            if os.path.exists(file):
                try: os.remove(file)
                except: pass
        return output_name
    return None
