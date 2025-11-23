import os
import google.generativeai as genai
import json
import logging
from dotenv import load_dotenv

load_dotenv()

class ContentGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logging.warning("GEMINI_API_KEY not found in environment variables.")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')

    def select_local_trend(self, trends_list):
        """
        Uses AI to identify the most relevant 'Local/Niche' trend for Kenya/Nairobi from a list.
        """
        prompt = f"""
        You are a trend analyst for a Kenyan digital agency.
        Here is a list of current trending topics: {trends_list}
        
        Task: Identify the ONE topic that is most likely to be a specific LOCAL issue to Kenya or Nairobi (e.g., local politics, local celebrity, Nairobi weather, Kenyan events) rather than a broad global topic (like 'Football' or 'Technology').
        
        If no clear local trend exists, pick the most niche/specific one.
        
        Output: Return ONLY the trend name exactly as it appears in the list. No explanations.
        """
        try:
            logging.info("Asking AI to select the best local trend...")
            response = self.model.generate_content(prompt)
            selected_trend = response.text.strip()
            
            # Basic validation to ensure it's in the list (fuzzy match or exact)
            # For now, just return it.
            logging.info(f"AI selected local trend: {selected_trend}")
            return selected_trend
        except Exception as e:
            logging.error(f"Error selecting local trend: {e}")
            return None

    def generate_content(self, trend, persona):
        """
        Generates content for a specific trend and persona.
        Returns a dictionary with content for Tweet, Facebook, Instagram, and TikTok.
        """
        prompt = self._construct_prompt(trend, persona)
        
        try:
            logging.info(f"Generating content for {persona['name']} on trend '{trend}'...")
            response = self.model.generate_content(prompt)
            
            # clean up response to ensure it's valid JSON
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3]
            elif text_response.startswith("```"):
                text_response = text_response[3:-3]
            
            content_data = json.loads(text_response)
            return content_data
        except Exception as e:
            logging.error(f"Error generating content: {e}")
            return None

    def _construct_prompt(self, trend, persona):
        return f"""
        You are a social media manager for '{persona['name']}'.
        
        **Brand Context:**
        - Role: {persona['role']}
        - Voice: {persona['voice']}
        - Content Focus: {', '.join(persona['content_focus'])}
        - Key Message/Tone: {persona.get('key_message') or persona.get('sample_tone')}
        - Hashtags: {', '.join(persona['hashtags'])}

        **Task:**
        Create social media content based on the trending topic: "{trend}".
        The content must bridge the trend to the brand's product/identity.

        **Required Outputs (JSON format):**
        1. "tweet": A short, engaging tweet (max 280 chars) with hashtags.
        2. "facebook_post": A slightly longer post suitable for Facebook.
        3. "instagram_reel_script": A script for a 15-30s Reel (Visuals + Audio + Caption).
        4. "tiktok_idea": A concept for a TikTok video (Hook + Action + Sound).

        **Output Format:**
        Provide ONLY the JSON object. Do not add any markdown formatting or extra text.
        {{
            "tweet": "...",
            "facebook_post": "...",
            "instagram_reel_script": "...",
            "tiktok_idea": "..."
        }}
        """

if __name__ == "__main__":
    # Test
    from config.personas import PERSONAS
    generator = ContentGenerator()
    # Mock generation if no key
    if os.getenv("GEMINI_API_KEY"):
        print(generator.generate_content("Artificial Intelligence", PERSONAS['agency']))
    else:
        print("Skipping generation test (No API Key)")
