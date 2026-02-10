# Complete Guide: Creating Manhwa & Webtoon Panels with Nano Banana Pro

## Overview

Nano Banana Pro (also known as Gemini 3 Pro Image or "Nano Banana 2") is Google's advanced AI image generation model that has become particularly popular for comic, manga, and manhwa creation. This guide compiles tips, techniques, and prompt strategies gathered from creators on X/Twitter, Reddit, YouTube tutorials, and specialized AI art communities.

---

## Table of Contents

1. [Why Nano Banana Pro Works for Manhwa](#why-nano-banana-pro-works-for-manhwa)
2. [Core Prompting Framework](#core-prompting-framework)
3. [Manhwa & Webtoon Specific Techniques](#manhwa--webtoon-specific-techniques)
4. [Character Consistency Strategies](#character-consistency-strategies)
5. [Panel Layout & Composition](#panel-layout--composition)
6. [Full-Page Generation Approach](#full-page-generation-approach)
7. [Ready-to-Use Prompt Templates](#ready-to-use-prompt-templates)
8. [Pro Tips from the Community](#pro-tips-from-the-community)
9. [Constraint-Based Prompting](#constraint-based-prompting)
10. [Colorization & Post-Processing](#colorization--post-processing)
11. [Tools & Platforms](#tools--platforms)
12. [Community Resources](#community-resources)

---

## Why Nano Banana Pro Works for Manhwa

Nano Banana Pro has several capabilities that make it particularly suited for manhwa/webtoon creation:

- **Full Page Generation**: Unlike older models that generate individual panels, Nano Banana Pro can generate an entire comic page in one go with natural panel divisions
- **Superior Character Consistency**: Maintains consistent character designs throughout multiple panels on the same page
- **Advanced Composition**: Handles complex panel layouts, dynamic perspectives, and seamless visual flow
- **Text Rendering**: Significantly improved text/speech bubble rendering compared to previous models
- **Reference Image Support**: Accepts reference images for style transfer and character consistency
- **Style Understanding**: Distinguishes between different comic styles (Shonen action lines vs. Shojo sparkles vs. Webtoon aesthetics)

---

## Core Prompting Framework

### The 6-Factor Basic Prompt Structure

Every Nano Banana Pro prompt should include these foundational elements:

| Factor | Description | Examples |
|--------|-------------|----------|
| **Subject** | Who and what is in the image | "A bartender," "A high school student," "A CEO" |
| **Composition** | Camera movements, framing | "Low angle shot," "Close-up," "Wide shot," "Bird's eye view" |
| **Action** | What is happening | "Working out," "Confessing love," "Fighting" |
| **Setting/Location** | Where the scene takes place | "Modern office," "Rainy street at night," "School rooftop" |
| **Style** | Art type and aesthetic | "Korean webtoon style," "Manhwa," "Full color vertical format" |
| **Editing Instructions** | For image remixing | "Replace background," "Change outfit," "Add rain effects" |

### Enhanced Prompt Factors

For higher quality results, add these additional details:

- **Aspect Ratio**: Vertical format (9:16 or 2:3) for webtoons, 3:4 for traditional panels
- **Camera Lens Details**: "f/1.8," "shallow depth of field," "dramatic lighting"
- **Shadow & Lighting**: "Long shadows," "Natural daylight," "Muted warm tones," "Dramatic backlighting"
- **Text Rendering**: Actual dialogue in quotation marks with placement instructions
- **Reference Inputs**: Mark the role of each input image (character, style, environment, background)

---

## Manhwa & Webtoon Specific Techniques

### Korean Webtoon Style Prompt Structure

```
Korean webtoon style, vertical panel format, full color.
[Setting description].
[Character description with specific features].
[Action/emotion being depicted].
[Lighting and atmosphere details].
--ar 9:16
```

### Example Webtoon Prompts

**Office Romance Scene:**
```
Korean webtoon style, vertical panel format, full color. A modern office setting with floor-to-ceiling windows. A handsome CEO with sleek black hair and a sharp blue suit is leaning over a desk, making eye contact with a nervous female employee. Soft office lighting, subtle pink blush effects on cheeks, romantic tension atmosphere. --ar 9:16
```

**Action Scene:**
```
Korean manhwa style, dynamic action panel. A young man with messy black hair in a school uniform throwing a powerful punch. Speed lines radiating from the impact point, debris flying, intense expression. High contrast, dramatic shadows, motion blur on the fist. Vertical format. --ar 2:3
```

**Emotional Close-Up:**
```
Webtoon style emotional close-up panel. A young woman with long dark hair and tears streaming down her face, rain falling around her. Soft focus background of city lights at night. Melancholic atmosphere, muted color palette with emphasis on blue tones. Sparkle effects on tears. --ar 9:16
```

---

## Character Consistency Strategies

Character consistency is one of the biggest challenges in AI-generated comics. Here are proven techniques:

### 1. Explicit Consistency Commands

Add these phrases to your prompts:
- "consistent character design across all panels, exact same face"
- "maintain identical facial features, bone structure, and appearance"
- "same character throughout, no variations in design"

### 2. Reference Image Workflow

1. **Create a Character Sheet First**: Generate a detailed character reference showing multiple angles
2. **Upload as Reference**: Use this sheet as a reference image for subsequent generations
3. **Describe Key Features**: Always include unique identifiers (hair color, eye color, distinctive marks, outfit details)

### 3. Character Sheet Prompt Template

```
Detailed character reference sheet for [character name].
Front view, 3/4 view, and side profile.
[Detailed physical description: hair, eyes, face shape, body type].
[Clothing description with colors and details].
[Distinctive features: scars, accessories, expressions].
Clean white background, professional character design layout.
Manhwa/webtoon art style, full color.
```

### 4. Multi-Panel Consistency Tips

- Number your panels explicitly in the prompt
- Reference "the same character from panel 1" in subsequent panel descriptions
- Keep a written record of your character's defining features for prompt consistency
- Use the same style keywords across all generations

---

## Panel Layout & Composition

### Explicit Layout Instructions

Be very specific about panel arrangements:

```
Create a 4-panel vertical webtoon page:
- Panel 1 (top, wide): Establishing shot of the city skyline
- Panel 2 (medium): Character walking through crowd, medium shot
- Panel 3 (small, left): Close-up of character's surprised eyes
- Panel 4 (large, bottom): Full reveal of what surprised them
```

### Camera Angle Keywords

| Angle | Use Case | Keywords |
|-------|----------|----------|
| Extreme Close-Up | Emotions, details | "ECU," "extreme close-up on eyes/lips" |
| Close-Up | Facial expressions | "close-up," "head shot" |
| Medium Shot | Upper body, conversations | "medium shot," "waist up" |
| Full Shot | Full body, action | "full body shot," "head to toe" |
| Wide/Establishing | Location, context | "wide shot," "establishing shot," "panoramic" |
| Low Angle | Power, intimidation | "low angle," "looking up at" |
| High Angle | Vulnerability, overview | "high angle," "bird's eye view" |
| Dutch Angle | Tension, unease | "tilted frame," "Dutch angle" |

### Composition Tips for Webtoons

- **Vertical Scrolling Flow**: Design panels to guide the eye downward
- **Varied Panel Sizes**: Mix large dramatic moments with smaller reaction shots
- **Breathing Room**: Include negative space for emotional beats
- **Gutter Space**: Mention "uniform spacing between panels" for clean layouts

---

## Full-Page Generation Approach

### Why Single-Panel Full-Page Works Best

Nano Banana Pro is optimized for full-page generation. Instead of generating individual panels:

1. **Use a single full-screen panel** that fills your entire page
2. **Describe the entire page layout** in your prompt
3. Let the AI create natural panel divisions and flow

### Benefits of This Approach

- Unified composition across the page
- Better character consistency within the page
- Dynamic, varied panel sizes that enhance storytelling
- Professional, publication-ready quality

### Full-Page Prompt Template

```
WORK SURFACE: Create a [X]-panel manhwa/webtoon page.

LAYOUT: [Describe arrangement - e.g., "Vertical strip with 4 panels of varying heights"]

CONTENT:
- Panel 1: [Description of first panel with camera angle and action]
- Panel 2: [Description of second panel]
- Panel 3: [Description of third panel]
- Panel 4: [Description of fourth panel]

STYLE: Korean webtoon aesthetic, full color, clean linework, soft shading.

CONSTRAINTS:
- No overlap between speech bubbles and faces
- Character design must remain identical across panels
- Uniform spacing between panels
- [Any other specific requirements]
```

---

## Ready-to-Use Prompt Templates

### Template 1: Romance Webtoon Scene

```
Korean webtoon style, vertical format, full color, 3-panel page.

Panel 1 (top, wide): A cozy café interior with warm lighting. Two characters sit across from each other at a small table - a nervous young woman with shoulder-length brown hair fidgeting with her coffee cup, and a handsome young man with dark hair watching her with a gentle smile.

Panel 2 (middle, medium shot): Close-up of their hands almost touching on the table. Soft pink sparkle effects around the scene. Warm golden hour lighting through the window.

Panel 3 (bottom, close-up): The woman's face, blushing deeply, eyes wide with surprise and hope. Subtle heart effects in the background.

Style: Soft shading, romantic atmosphere, pastel color palette with warm tones. Clean linework typical of popular romance webtoons. --ar 9:16
```

### Template 2: Action Manhwa Sequence

```
Dynamic Korean manhwa action sequence, black and white with screentones, 4-panel vertical page.

Panel 1 (small, top): Extreme close-up of protagonist's determined eyes, speed lines in background.

Panel 2 (large, diagonal): Wide shot of protagonist mid-leap between rooftops, coat flowing dramatically, urban nightscape below. Heavy use of motion lines.

Panel 3 (medium): Impact moment - fist connecting with enemy, shockwave effects radiating outward, debris flying. "impact frame" composition.

Panel 4 (bottom, horizontal): Landing pose, crouched low, looking back over shoulder with intense expression. Dramatic shadows, dust settling.

Style: High contrast, heavy inking, G-pen texture, dynamic composition with extreme perspectives. Shonen manga influence with manhwa aesthetics. --ar 2:3
```

### Template 3: Emotional Drama Beat

```
Korean webtoon emotional scene, full color, vertical 3-panel format.

Panel 1 (top, establishing): Rainy city street at night, neon signs reflected in puddles. A lone figure stands under a streetlight, small in frame to emphasize isolation.

Panel 2 (middle, medium shot): The character from behind, shoulders trembling. Rain soaking through their clothes. Muted blue-gray color palette.

Panel 3 (bottom, close-up): Face in profile, single tear mixing with raindrops. Eyes reflecting city lights. Melancholic but beautiful composition.

Style: Atmospheric, cinematic lighting, detailed rain effects, emotional color grading with emphasis on blues and grays. Soft, painterly rendering style popular in drama webtoons. --ar 9:16
```

### Template 4: Fantasy/Isekai Scene

```
Korean fantasy manhwa style, full color vertical page, 4 panels.

Panel 1 (wide establishing): Massive floating islands with waterfalls, magical crystals glowing, fantastical architecture. Our protagonist small in frame, looking up in awe.

Panel 2 (medium): Protagonist's amazed reaction, wind blowing their hair. Portal closing behind them with magical particle effects.

Panel 3 (close-up): A mysterious guide character appears - elaborate fantasy outfit, pointed ears, glowing markings on skin. Enigmatic smile.

Panel 4 (dialogue panel): Both characters, guide gesturing toward the landscape. Speech bubble: "Welcome to the realm between worlds."

Style: Vibrant saturated colors, detailed fantasy environments, clean character designs with flowing hair and dramatic clothing. Magical glow effects and particle systems. --ar 9:16
```

---

## Pro Tips from the Community

### Tips Gathered from X/Twitter and Reddit

1. **Number Your Panels**: "Panel 1, Panel 2, Panel 3..." helps the AI understand sequence
2. **Add SFX Instructions**: "SFX in comic font" for sound effects like "POW!" or "THWAP!"
3. **Specify Text Sharpness**: "Text must be sharp at small sizes" prevents blurry dialogue
4. **Use Reference Photos**: Upload clear character references for dramatically improved consistency
5. **Iterate Quickly**: "Make panel 6 more dramatic low angle" works for quick refinements
6. **Batch Generate**: Create character sheets first, then use as references for all subsequent pages

### What Works Best According to Creators

- **Detailed descriptions beat vague requests**: "Draw a manhwa page" fails; detailed panel-by-panel descriptions succeed
- **Style keywords matter**: Include "Korean webtoon style" or "manhwa aesthetic" explicitly
- **Emotional descriptors help**: "tense atmosphere," "romantic tension," "melancholic mood"
- **Technical terms are understood**: "screentones," "speed lines," "impact frames," "chibi reaction"

---

## Constraint-Based Prompting

### The Google-Recommended Structure

According to Google's official guidelines, Nano Banana Pro responds best to constraint-rich prompts. Structure your prompts like a design document:

```
WORK SURFACE: [Define what you're creating - comic page, single panel, character sheet]

LAYOUT: [Specific arrangement instructions]

COMPONENTS: [List all elements that need to appear]
• main character
• background elements
• speech bubbles
• effects (speed lines, sparkles, etc.)

STYLE: [Artistic direction]
[Era/genre] aesthetic, [color palette], [line quality], [mood/lighting]

CONSTRAINTS: [Rules the AI must follow]
• No overlap between balloons and faces
• Character design must remain identical across panels
• Uniform spacing between panels
• [Specific requirements]

SOURCE MATERIAL: [The actual content/story]
Panel 1: [Description]
Panel 2: [Description]
...

INTERPRETATION: [Emotional/thematic guidance]
Convey [emotion], [atmosphere], sense of [theme].
```

### Example Using Constraint Structure

```
WORK SURFACE: Create a 3-panel webtoon page.

LAYOUT: Vertical strip layout, panels stacked. Top panel largest (40%), middle medium (30%), bottom smallest (30%).

COMPONENTS:
• Female protagonist (short black hair, school uniform, determined expression)
• Male antagonist (tall, silver hair, menacing aura)
• School hallway background
• Dramatic lighting from windows
• One speech bubble in panel 2

STYLE: Modern Korean webtoon aesthetic. Clean linework, soft cel-shading, full color with slightly desaturated palette. Dramatic shadows.

CONSTRAINTS:
• No overlap between speech bubble and faces
• Character proportions consistent across all panels
• Eye level changes to show power dynamic (low angle on antagonist)
• Maintain 20px equivalent spacing between panels

SOURCE MATERIAL:
Panel 1: Wide shot - Protagonist faces antagonist in empty hallway, 10 meters apart. Tension.
Panel 2: Medium shot - Antagonist speaks, "You shouldn't have come here." Threatening smile.
Panel 3: Close-up - Protagonist's eyes, fire reflected in them. Defiant.

INTERPRETATION: Convey confrontation, courage against overwhelming odds, the calm before the storm.
```

---

## Colorization & Post-Processing

### Colorizing Black & White Manhwa

Nano Banana Pro can colorize existing line art:

```
Take this black and white manga/manhwa panel and add full color.
Maintain all original linework exactly.
Color palette: [describe desired colors]
Lighting: [describe light source and mood]
Style: [Korean webtoon coloring / cel-shaded / painterly]
Preserve all details, add appropriate shading and highlights.
```

### Color Style Keywords

- **Soft cel-shading**: Clean, anime-style coloring with defined shadows
- **Painterly**: More artistic, brushstroke-visible coloring
- **Flat colors**: Simple fills without complex shading
- **Gradient shading**: Smooth color transitions
- **Watercolor effect**: Soft, bleeding edges on colors

---

## Tools & Platforms

### Where to Use Nano Banana Pro

| Platform | Features | Cost |
|----------|----------|------|
| **Google Gemini** | Direct access, reference images | Free tier limited, Advanced for unlimited |
| **Mew Design** | AI design agent, batch generation, conversational refinement | Free credits on signup |
| **Anifusion** | Comic-specific features, panel tools, character sheets | Free tier available |
| **Filmora** | Video integration, pre-built templates | Subscription |
| **GlobalGPT** | Multi-model access, batch generation | Subscription |

### Workflow Recommendations

1. **For Beginners**: Start with Gemini directly to learn prompting
2. **For Series Work**: Use Mew Design or Anifusion for better consistency tools
3. **For Post-Processing**: Combine AI generation with Photoshop/Clip Studio for final polish

---

## Community Resources

### Where to Find More Prompts & Tips

- **GitHub**: [awesome-nanobanana-pro](https://github.com/ZeroLu/awesome-nanobanana-pro) - Curated prompts from X, WeChat, and top creators
- **PromptHero**: Browse community-submitted Nano Banana prompts
- **Reddit**: r/Bard, r/ArtificialIntelligence for discussions and experiments
- **X/Twitter**: Search "Nano Banana Pro comic" or "Nano Banana Pro webtoon" for latest discoveries
- **YouTube**: Search for tutorial videos on Nano Banana Pro comic creation

### Active Creator Communities

Creators are actively sharing:
- Full webtoon series (50+ pages)
- Character consistency techniques
- Style transfer experiments
- Prompt refinement discoveries

---

## Quick Reference Cheat Sheet

### Essential Keywords for Manhwa/Webtoon

```
Style: Korean webtoon style, manhwa aesthetic, full color, vertical format
Format: --ar 9:16, --ar 2:3, vertical panel format
Consistency: consistent character design across all panels, exact same face
Effects: speed lines, impact stars, emotional sparkles, sweat drops, blush effects
Mood: romantic tension, dramatic atmosphere, melancholic, action-packed
Technical: clean linework, soft cel-shading, screentones, G-pen texture
```

### Panel Description Formula

```
[Panel number] ([size/position]): [Camera angle] of [subject] [doing action] in [setting]. [Mood/atmosphere]. [Special effects if any].
```

### Quick Fixes

- Characters look different → Add "exact same face, identical features"
- Layout wrong → Be more explicit about panel arrangement
- Not stylized enough → Add "Korean webtoon style, manhwa aesthetic"
- Text blurry → Add "sharp text rendering, clear speech bubbles"
- Too realistic → Add "anime style, cel-shaded, clean linework"

---

## Conclusion

Nano Banana Pro represents a significant leap forward for AI-assisted manhwa and webtoon creation. The key to success lies in:

1. **Structured, detailed prompts** rather than vague requests
2. **Explicit style keywords** for Korean webtoon aesthetics
3. **Character consistency strategies** using references and explicit descriptions
4. **Constraint-based prompting** that treats prompts like design documents
5. **Community learning** - the techniques are evolving rapidly

The barrier to creating professional-looking webtoon content has dropped significantly. With practice and the techniques in this guide, you can create publication-quality manhwa panels and pages.

---

*Last Updated: January 2026*
*Sources: Google official guidelines, Mew Design, Anifusion, Radical Curiosity, PromptHero, GitHub awesome-nanobanana-pro, community discoveries on X/Twitter and Reddit*
