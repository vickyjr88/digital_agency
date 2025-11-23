# PROJECT CONTEXT: The "Agency-in-a-Box" Automation System

## 1. Project Overview
**Objective:** Build a Python-based "Digital Employee" that automates content marketing for a parent digital agency and its three portfolio ventures.
**Primary Goal:** Use the portfolio ventures as "Live Case Studies" to demonstrate the agency's capabilities to future clients.
**Core Loop:** Detect Trends (Google Trends) → Generate Content (Gemini API) → Human Approval (CLI) → Publish (Twitter/Facebook APIs).

---

## 2. Brand Architecture & Personas

### A. Parent Entity: The Digital Agency (Name TBD)
* **Role:** The strategist and architect.
* **Voice:** Professional, data-driven, authoritative, results-oriented.
* **Content Focus:** "Building in public," sharing results from the portfolio ventures, marketing tips, B2B growth strategies.
* **Key Message:** "We don't just sell marketing; we practice it on our own businesses."

### B. Portfolio Venture 1: Drip Emporium
* **Domain:** `dripemporium.store`
* **Business Type:** E-commerce / Fashion Merch.
* **Voice:** Gen Z, Hypebeast, Nairobi Streetwear, energetic, visual.
* **Content Focus:** Outfit inspiration, pop-culture tie-ins, flash sales, "Fit Check" posts.
* **Sample Tone:** "Nairobi is cold but the drip is hot. 🧊🔥 Grab the new hoodie before it vanishes."

### C. Portfolio Venture 2: Sheng Mtaa
* **Domain:** `shengmtaa.com`
* **Business Type:** Local Slang Dictionary / Media.
* **Voice:** Relatable, funny, community-focused, heavy use of Sheng slang.
* **Content Focus:** Word of the day, translating trending news into Sheng, engagement questions.
* **Sample Tone:** "Form ni gani leo? Usiachwe nyuma, cheki definition ya leo."

### D. Portfolio Venture 3: Vital Digital Media
* **Domain:** `vitaldigitalmedia.net`
* **Business Type:** Web Development & Hosting Company.
* **Voice:** Tech-savvy, helpful, educational, reliable.
* **Content Focus:** Website speed tips, hosting uptime, "Why you need a website," technical SEO.
* **Sample Tone:** "Is your website loading in under 3 seconds? If not, you're losing customers. Here is why."

---

## 3. Technical Architecture

### The "Digital Employee" Logic
1.  **Trend Spotter (Input):**
    * Uses `pytrends` to fetch top 3 trending searches in Kenya (Geo: `KE`).
2.  **Content Generator (Processing):**
    * Uses Google Gemini API (`gemini-2.0-flash`).
    * **Prompt Logic:** "Take [Trend X], adopt [Persona Y], and write a social media post that bridges the trend to the brand's product."
3.  **The Staging Area (Human-in-the-Loop):**
    * **CRITICAL:** Do not auto-post.
    * Save generated drafts to a JSON file (`drafts.json`) or display in CLI for `Y/N` approval.
4.  **The Publisher (Output):**
    * Twitter (X) API (Free/Basic tier) via `tweepy`.
    * Facebook Graph API via `facebook-sdk`.

---

## 4. Operational Constraints
* **Language:** English (UK/Kenya) mixed with Sheng for the "Sheng Mtaa" brand.
* **Hashtags:** Always include #Kenya #Nairobi and 1 brand-specific tag.
* **Tone Check:** Ensure Drip Emporium never sounds "corporate" and Vital Digital never sounds "slang-heavy."
