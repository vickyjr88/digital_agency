import os
import google.generativeai as genai
import json
import logging
from dotenv import load_dotenv

load_dotenv()

import openai

class ContentGenerator:
    def __init__(self):
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            logging.error("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables.")
            self.model = None
        else:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logging.info("ContentGenerator initialized successfully with Gemini API")
            except Exception as e:
                logging.error(f"Failed to initialize Gemini model: {e}")
                self.model = None

        # Initialize OpenAI (Fallback)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
            logging.info("OpenAI fallback initialized successfully")
        else:
            self.openai_client = None
            logging.warning("OPENAI_API_KEY not found. ChatGPT fallback disabled.")

    def select_local_trend(self, trends_list):
        """
        Uses AI to identify the most relevant 'Local/Niche' trend for Kenya/Nairobi from a list.
        """
        if not self.model and not self.openai_client:
            logging.error("Cannot select trend: No AI models initialized")
            return trends_list[0] if trends_list else None
            
        prompt = f"""
        You are a trend analyst for a Kenyan digital agency.
        Here is a list of current trending topics: {trends_list}
        
        Task: Identify the ONE topic that is most likely to be a specific LOCAL issue to Kenya or Nairobi (e.g., local politics, local celebrity, Nairobi weather, Kenyan events) rather than a broad global topic (like 'Football' or 'Technology').
        
        If no clear local trend exists, pick the most niche/specific one.
        
        Output: Return ONLY the trend name exactly as it appears in the list. No explanations.
        """
        
        # Try Gemini first
        if self.model:
            try:
                logging.info("Asking Gemini to select the best local trend...")
                response = self.model.generate_content(prompt)
                selected_trend = response.text.strip()
                logging.info(f"Gemini selected local trend: {selected_trend}")
                return selected_trend
            except Exception as e:
                logging.error(f"Gemini failed to select trend: {e}")
        
        # Fallback to OpenAI
        if self.openai_client:
            try:
                logging.info("Asking ChatGPT (fallback) to select the best local trend...")
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                selected_trend = response.choices[0].message.content.strip()
                logging.info(f"ChatGPT selected local trend: {selected_trend}")
                return selected_trend
            except Exception as e:
                logging.error(f"ChatGPT failed to select trend: {e}")
                
        return trends_list[0] if trends_list else None

    def generate_content(self, trend, persona):
        """
        Generates content for a specific trend and persona.
        Returns a dictionary with content for Tweet, Facebook, Instagram, and TikTok.
        """
        if not self.model and not self.openai_client:
            logging.error("Cannot generate content: No AI models initialized.")
            return None
            
        prompt = self._construct_prompt(trend, persona)
        
        # Try Gemini first
        if self.model:
            try:
                logging.info(f"Generating content with Gemini for {persona['name']} on trend '{trend}'...")
                response = self.model.generate_content(prompt)
                return self._parse_response(response.text)
            except Exception as e:
                logging.error(f"Gemini generation failed: {e}")
        
        # Fallback to OpenAI
        if self.openai_client:
            try:
                logging.info(f"Generating content with ChatGPT (fallback) for {persona['name']} on trend '{trend}'...")
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",  # Use GPT-4 for better creative writing
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                return self._parse_response(response.choices[0].message.content)
            except Exception as e:
                logging.error(f"ChatGPT generation failed: {e}")
                
        return None

    def _parse_response(self, text_response):
        """Helper to parse JSON response from AI models"""
        try:
            text_response = text_response.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3]
            elif text_response.startswith("```"):
                text_response = text_response[3:-3]
            
            return json.loads(text_response)
        except Exception as e:
            logging.error(f"Error parsing AI response: {e}")
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
