import os
import sys
import pygame
import groq
import re
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. INITIALIZATION & DATA (Resets when closed)
# ---------------------------------------------------------
load_dotenv()
api_key = os.getenv("GROQ_KEY")
client = groq.Groq(api_key=api_key)

pygame.init()
screen = pygame.display.set_mode((1000, 500))
pygame.display.set_caption("NPC Data Science Quest")
font = pygame.font.Font(None, 28) # Slightly smaller font for better wrapping
clock = pygame.time.Clock()

# --- NPC STATS ---
all_npc_stats = {
    "Jerry": {
        "is_skeleton": True,
        "has_been_taught": False,
        "learned_skills": [],
        "description": "...",
        "chat_history": [], # IMPORTANT
        "ui_history": [],   # IMPORTANT
        "personality": "",  # IMPORTANT
        "message_count": 0,  # Counts how many times Jerry has spoken (for unlocking assessment)
        "affinity": 0      # This will be calculated based on interactions with the other NPCs
    },
    "Meridian": {"affinity": 20, "category": "intelligence", "teaching_list": [], "personality": "A mysterious wizard.","chat_history": [], "ui_history": []},
    "Atlas": {"affinity": 20, "category": "strength", "teaching_list": [], "personality": "A mighty warrior.","chat_history": [], "ui_history": []},
    "Krake": {"affinity": 20, "category": "coolness", "teaching_list": [], "personality": "A laid-back traveler.","chat_history": [], "ui_history": []}
}

# ---------------------------------------------------------
# 2. HELPER FUNCTIONS (The "Engine")
# ---------------------------------------------------------

def load_sprite_sheet(filename, cols, rows, scale=None):
    sheet = pygame.image.load(filename).convert_alpha()
    w, h = sheet.get_width() // cols, sheet.get_height() // rows
    sprites = []
    for row in range(rows):
        for col in range(cols):
            frame = sheet.subsurface(pygame.Rect(col * w, row * h, w, h))
            if scale: frame = pygame.transform.scale(frame, scale)
            sprites.append(frame)
    return sprites

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines, current_line = [], ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] < max_width:
            current_line = test_line
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    lines.append(current_line.strip())
    return lines

def get_llm_response(player_text, npc_name):
    stats = all_npc_stats[npc_name]
    
    # --- Instructions ---
    if npc_name == "Jerry":
        system_content = f"""

        You are Jerry, a skeleton student newly awakened by necromancy.

        Current Personality Profile: {stats['personality']}

       

        Rules for Jerry:

        1. You are curious, slightly confused, and eager to please your master.

        2. Speak about the skills you have learned: {', '.join(stats['learned_skills'])}.

        3. Do NOT try to teach the player or use DATA{{new_teach}}.

        4. Keep replies under 20 words.

        5.Dont use ant non ASCII characters

        6. Never discuss your stats

        7. Do not be rude or violent. Do not condone that behavior

        """

    else:

        # The Master Teachers' prompt (Meridian, Atlas, Krake)

        system_content = f"""

        You are {npc_name}, a master of {stats['category']}. You have. {stats['personality']}

        Current Affinity: {stats['affinity']}/100.

       

        Rules for Masters:

        1. Teach the player skills for their skeleton using DATA{{new_teach: "SKILL"}}.

        Skills can be related to anything you like.

        You should mention the skills in your dialogue to make it clear to the player what you are teaching, but the DATA tag is how the game tracks it.

        You should be subtle about the skills and not just list them out. Roleplay as the character and weave the teachings into your dialogue naturally.

        You should encourage the player to teach Jerry these skills, but do not force them. The player may choose to roleplay or interact in ways that don't always lead to teaching, and that's okay!

        When a character asks for a skill to be taught you must respond with the DATA tag, but you can also include the skill name in your dialogue to make it clear. For example, if teaching "Deadlifts", you might say "Ah, I see you are interested in Deadlifts. Let me show you how to do them." and include DATA{{new_teach: "Deadlifts"}} in your response.

        2. Adjust affinity using DATA{{affinity_change: NUMBER}}. Affinity should increase in increments of 10 or 20 for positive interactions, and decrease in increments of 5 or 10 for negative interactions.

        3. Keep replies under 15 words.

        5. Never Mention your affinity or the DATA tags in your replies. These are for the player's understanding only.

        6. Always respond to the player's message, even if it's just a simple greeting. Do not ignore any player input.

        7. Always keep the DATA{{new_teach: "SKILL"}} tag in your response if you are teaching a skill, and the DATA{{affinity_change: NUMBER   }} tag if you are changing affinity. These tags are how the player understands the impact of their interactions with you.

        8.  Dont use ant non ASCII characters

        9. Do not be rude or violent. Do not condone that behavior

        """



    # Build payload
    messages_for_ai = [{"role": "system", "content": system_content}]
    messages_for_ai.extend(stats["chat_history"][-6:])
    
    # REINFORCEMENT: We add a hidden prompt after the user text
    reinforced_user_text = f"{player_text}\n(Reminder: Always include your DATA tags at the end of your response.)"
    messages_for_ai.append({"role": "user", "content": reinforced_user_text})

    completion = client.chat.completions.create(
        messages=messages_for_ai,
        model="llama-3.1-8b-instant",
        temperature=0.7 # Adding a bit of "creativity" helps it follow complex formatting
    )
    
    return completion.choices[0].message.content

def process_npc_reply(raw_text, npc_name):

    match = re.search(r"DATA\{(.*?)\}", raw_text)

    clean_message = raw_text

    if match:

        data_str = match.group(1)

        aff_match = re.search(r"affinity_change:\s*(-?\d+)", data_str)

        if aff_match:

            all_npc_stats[npc_name]["affinity"] += int(aff_match.group(1))

        teach_match = re.search(r'new_teach:\s*\"([^\"]+)\"', data_str)

        if teach_match and "None" not in teach_match.group(1):

            all_npc_stats[npc_name]["teaching_list"].append(teach_match.group(1))

        clean_message = re.sub(r"DATA\{.*?\}", "", raw_text).strip()

        if teach_match:

            skill_name = teach_match.group(1)

   

            # Run the math instead of printing

            result_message = try_teaching_jerry(skill_name, npc_name)

   

            # Add this "System Message" to the chat so the player sees it

            all_npc_stats[current_npc]["ui_history"].append(f"*** {result_message} ***")

    return clean_message
# --------------------------------
# 2. Pygame Initialization
# --------------------------------

pygame.init()
screen = pygame.display.set_mode((1000, 500))
pygame.display.set_caption("NPC Data Science Quest")
font = pygame.font.Font(None, 32)
clock = pygame.time.Clock()

# Load Backgrounds
world_bg = pygame.transform.scale(pygame.image.load("assets/setting/forest_/main_area.jpg"), (1000, 500))
desert_bg = pygame.transform.scale(pygame.image.load("assets/setting/desert_/desert_main.jpg"), (1000, 500))
mountain_bg = pygame.transform.scale(pygame.image.load("assets/setting/cave_/cave_main.jpg"), (1000, 500))
connect_bg = pygame.transform.scale(pygame.image.load("assets/setting/forest_/connect_main.jpg"), (1000, 500))
chat_bg = pygame.transform.scale(pygame.image.load("assets/chat_background.png"), (1000, 500))

# Sprites
player_sprites = load_sprite_sheet("assets/sprite/Enemy/Enemy 02-1.png", 3, 4, (70, 70))
npc_sprites = load_sprite_sheet("assets/sprite/Enemy/Enemy 06-1.png", 3, 4, (70, 70))
intel_sprite = load_sprite_sheet("assets/sprite/Female/Female 25-1.png", 3, 4, (70, 70))
strength_sprite = load_sprite_sheet("assets/sprite/Male/Male 01-4.png", 3, 4, (70, 70))
cool_sprite = load_sprite_sheet("assets/sprite/Female/Female 10-2.png", 3, 4, (70, 70))

# Rects
player_rect = pygame.Rect(50, 260, 70, 70)
world_npc_rect = pygame.Rect(625, 220, 70, 70)   # Jerry
intel_npc_rect = pygame.Rect(445, 170, 70, 70)   # Meridian
strength_npc_rect = pygame.Rect(465, 170, 70, 70) # Atlas
cool_npc_rect = pygame.Rect(280, 350, 70, 70)    # Krake

# Gates
RIGHT_GATE = pygame.Rect(990, 0, 10, 500)
LEFT_GATE = pygame.Rect(0, 0, 10, 500)
TOP_GATE = pygame.Rect(0, 0, 1000, 10)
BOTTOM_GATE = pygame.Rect(0, 490, 1000, 10)


# --------------------------------
# 3. Drawing Functions
# --------------------------------
def draw_title_screen():
    screen.fill((10, 10, 30))
    title_text = font.render("Elements of Necromancy: Conversation", True, (255, 215, 0))
    # Direct the player to the Info Panel first
    start_text = font.render("Press SPACE to Begin Setup", True, (255, 255, 255))
    
    screen.blit(title_text, (290, 150))
    screen.blit(start_text, (350, 250))

def draw_info_panel():
    screen.fill((20, 20, 20))
    instructions = [
        "--- PROJECT JERRY: SYSTEM OVERVIEW ---",
        "1. OBJECTIVE: Teach the hollow skeleton Jerry Conversation.",
        "2. SOURCES: Visit Meridian (Intel), Atlas (Str), and Krake (Cool)",
        "3. PROCESS: Bond with them and let them teach Jerry skills",
        "4. FINAL STEP: After 10+ messages with Jerry, assess Jerry's skill level.",
        "5. PASS NECROMANCY CONVERSATION COMPONENT (hopefully)",
        
        "",
        "SYSTEM READY.",
        "Press ENTER to initialize Main Game."
    ]
    
    for i, line in enumerate(instructions):
        color = (255, 255, 255)
        if "ENTER" in line: color = (0, 255, 0) # Highlight the final prompt
        text_surf = font.render(line, True, color)
        screen.blit(text_surf, (100, 100 + (i * 40)))

def draw_world(game_state): # We don't need the second param for static NPCs
    # 1. Forest / Main Area
    if game_state == "world":
        screen.blit(world_bg, (0, 0))
        screen.blit(npc_sprites[0], world_npc_rect) # Draw Jerry
        
    # 2. Connection Area (Krake/Kyle)
    elif game_state == "connect":
        screen.blit(connect_bg, (0, 0))
        screen.blit(cool_sprite[0], cool_npc_rect)  # Krake is always here
        
    # 3. Desert (Meridian)
    elif game_state == "desert":
        screen.blit(desert_bg, (0, 0))
        screen.blit(intel_sprite[0], intel_npc_rect) # Meridian is always here
        
    # 4. Mountain (Atlas)
    elif game_state == "mountain":
        screen.blit(mountain_bg, (0, 0))
        screen.blit(strength_sprite[0], strength_npc_rect) # Atlas is always here


def draw_chat(current_npc, messages, player_input):
    screen.blit(chat_bg, (0,0))
    
    # --- ENLARGE AND RECENTER NPC PORTRAIT ---
    portrait_size = (400, 400) # Enlarge them here
    center_x = (screen.get_width() // 2) - (portrait_size[0] // 2)
    portrait_y = 20 # Keep them slightly higher than the chat box
    
    # Select the raw sprite based on NPC
    raw_sprite = None
    if current_npc == "Jerry":
        raw_sprite = npc_sprites[0]
    elif current_npc == "Meridian":
        raw_sprite = intel_sprite[0]
    elif current_npc == "Atlas":
        raw_sprite = strength_sprite[0]
    elif current_npc == "Krake":
        raw_sprite = cool_sprite[0]

    # Scale and Blit if we found a sprite
    if raw_sprite:
        big_portrait = pygame.transform.scale(raw_sprite, portrait_size)
        screen.blit(big_portrait, (center_x, portrait_y))

    # --- Draw Main Chat Panel ---
    pygame.draw.rect(screen, (0,0,0), (150, 340, 700, 140))
    
    # Draw Wrapped Messages
    y_pos = 350
    max_w = 660 
    all_lines = []
    for msg in messages:
        for line in wrap_text(msg, font, max_w):
            all_lines.append(line)
    
    for line in all_lines[-4:]: 
        screen.blit(font.render(line, True, (255,255,255)), (170, y_pos))
        y_pos += 25

    # Draw Input Line
    input_line = wrap_text("> " + player_input, font, max_w)[0]
    screen.blit(font.render(input_line, True, (255, 255, 0)), (170, y_pos))

    # --- NEW BUTTON PLACEMENT (Top Right) ---
    if current_npc == "Jerry" and all_npc_stats["Jerry"]["message_count"] >= 10:
        # Define the Button Rect
        button_rect = pygame.Rect(750, 20, 230, 60)
        
        # Draw a golden border/glow
        pygame.draw.rect(screen, (212, 175, 55), (button_rect.x-2, button_rect.y-2, button_rect.w+4, button_rect.h+4), border_radius=10)
        # Draw the button body
        pygame.draw.rect(screen, (50, 50, 50), button_rect, border_radius=10)
        
        btn_text = font.render("ASSESS JERRY", True, (255, 215, 0))
        # Center text in button
        screen.blit(btn_text, (button_rect.x + 25, button_rect.y + 18))

def draw_assessment_screen():
    screen.fill((20, 20, 20)) # Dark background
    jerry = all_npc_stats["Jerry"]
    title = font.render("--- JERRY'S CAPACITY ---", True, (255, 215, 0))
    screen.blit(title, (300, 50))
    # Draw Stats
    stats_y = 120
    stats_text = [
        f"Intelligence: {jerry['intelligence']}",
        f"Strength: {jerry['strength']}",
        f"Charisma: {jerry['charisma']}",
        f"Skills: {', '.join(jerry['learned_skills'])}"
    ]
    for line in stats_text:
        surf = font.render(line, True, (255, 255, 255))
        screen.blit(surf, (100, stats_y))
        stats_y += 40
    # Draw Groq's Evaluation
    eval_lines = wrap_text(f"ASSESSOR'S VERDICT: {jerry['evaluation']}", font, 800)
    for line in eval_lines:
        eval_surf = font.render(line, True, (0, 255, 0))
        screen.blit(eval_surf, (100, stats_y + 20))
        stats_y += 30
    prompt = font.render("Press ESC to return to game and Improve Score", True, (150, 150, 150))
    screen.blit(prompt, (275, 450))

# --------------------------------
# 3. Game Loop Variables
# --------------------------------

game_state = "title"
previous_state = "world"
current_npc = None
player_input = ""
messages = []
frozen = False

# --------------------------------
# 4. Logic Functions
# --------------------------------
import random

def try_teaching_jerry(skill, teacher_name):
    teacher_stats = all_npc_stats[teacher_name]
    jerry_stats = all_npc_stats["Jerry"]
    # 1. Probability Calculation: (Affinity / 100)
    # If Affinity is 75, success chance is 75%
    success_roll = random.randint(1, 100)
    if success_roll <= teacher_stats["affinity"]:
        if skill not in jerry_stats["learned_skills"]:
            jerry_stats["learned_skills"].append(skill)
            jerry_stats["has_been_taught"] = True
            return f"SUCCESS: Jerry has learned {skill}!"
    else:
        return f"FAILURE: Your bond with {teacher_name} wasn't strong enough and they didn't put enough effort in."

def handle_movement(keys):
    speed = 4
    if keys[pygame.K_LEFT]: player_rect.x -= speed
    if keys[pygame.K_RIGHT]: player_rect.x += speed
    if keys[pygame.K_UP]: player_rect.y -= speed
    if keys[pygame.K_DOWN]: player_rect.y += speed
    player_rect.x = max(0, min(player_rect.x, 930))
    player_rect.y = max(0, min(player_rect.y, 430))

def check_transitions():
    global game_state
    if game_state == "world" and player_rect.colliderect(LEFT_GATE):
        game_state = "connect"; player_rect.x = 920
    elif game_state == "connect":
        if player_rect.colliderect(RIGHT_GATE): game_state = "world"; player_rect.x = 20
        elif player_rect.colliderect(TOP_GATE): game_state = "mountain"; player_rect.y = 420
        elif player_rect.colliderect(BOTTOM_GATE): game_state = "desert"; player_rect.y = 20
    elif game_state == "mountain" and player_rect.colliderect(BOTTOM_GATE):
        game_state = "connect"; player_rect.y = 20
    elif game_state == "desert" and player_rect.colliderect(TOP_GATE):
        game_state = "connect"; player_rect.y = 420

def get_active_npc():
    """Returns the NPC name if player is colliding with them in the correct state."""
    if game_state == "world" and player_rect.colliderect(world_npc_rect):
        jerry_stats = all_npc_stats["Jerry"]

        # Scenario B: Jerry is hollow, check if we can wake him up
        total_teachings = len(jerry_stats["learned_skills"])
        
        if total_teachings > 0:
            # We set the flag here so the game knows he is permanently awake
            jerry_stats["has_been_taught"] = True
            return "Jerry" 
        else:
            return "Locked_Jerry"

    # ... rest of your masters check ...
    if game_state == "connect" and player_rect.colliderect(cool_npc_rect): return "Krake"
    if game_state == "desert" and player_rect.colliderect(intel_npc_rect): return "Meridian"
    if game_state == "mountain" and player_rect.colliderect(strength_npc_rect): return "Atlas"
    return None

def generate_jerry_personality():
    jerry_stats = all_npc_stats["Jerry"]
    skills = jerry_stats["learned_skills"]
    if not skills:
        return "A silent, hollow skeleton waiting for a spark of life."

    # Base personality
    base = "You are Jerry, a skeleton brought to life by the teachings of others. You are eager to learn and adapt, but your personality is still forming. You can learn from the players personality"
    # Dynamic traits based on who taught him
    traits = []
    traits.append(f"The Quality:You have a thirst for knowledge, a curious mind and intelligence. Is embodied in you {all_npc_stats['Meridian']['affinity']}/100" )
    traits.append(f"The Quality:You have physical prowess and strength of mind and body. Is embodied in you {all_npc_stats['Atlas']['affinity']}/100" )
    traits.append(f"The Quality:You have a laid-back attitude and a knack for social interactions. Is embodied in you {all_npc_stats['Krake']['affinity']}/100" )

    personality_string = base + " ".join(traits) + f" You currently know these skills: {', '.join(skills)}."
    return personality_string

#Assessment:

all_npc_stats["Jerry"].update({
    "intelligence": 0,
    "strength": 0,
    "charisma": 0,
    "evaluation": "" # This will store Groq's 1-10 rating
})

def get_final_assessment():
    jerry = all_npc_stats["Jerry"]
    # Aggregate data for the "Judge"
    intel = all_npc_stats["Meridian"]["affinity"]
    stre = all_npc_stats["Atlas"]["affinity"]
    char = all_npc_stats["Krake"]["affinity"]
    skills = ", ".join(jerry["learned_skills"])

    prompt = f"""
    The student Jerry (a skeleton) has completed his training.
    Stats: Intelligence {intel}/100, Strength {stre}/100, Charisma {char}/100.
    Skills Mastered: {skills}.
    
    Provide a rating from 1-10 on the Necromancer's teaching capacity and a 
    short 20 word summary of Jerry's new personality. for the first 6 points add up the affinity scores and multiply by 0.02, for points 7-10 add 0.5 points for each skill learned, and for a perfect 10, all three affinities must be 100 and at least 8 skills learned.
    Dont use ant non ASCII characters or new lines.
    Follow this format strictly: "RATING: X/10. SUMMARY: [20 word summary here]"
    """
    # Call Groq (this might take a second, so the game might 'pause' briefly)
    response = client.chat.completions.create(
        messages=[{"role": "system", "content": "You are the High Lich Examiner."},
            {"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
    )
    # Store the result in Jerry's stats for the draw function to see
    jerry["intelligence"] = intel
    jerry["strength"] = stre
    jerry["charisma"] = char
    jerry["evaluation"] = response.choices[0].message.content

# --------------------------------
# 5. Main Loop
# --------------------------------

while True:
    for event in pygame.event.get():
        
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()



        if event.type == pygame.KEYDOWN:
            # 1. TITLE -> INFO
            if game_state == "title":
                if event.key == pygame.K_SPACE:
                    game_state = "info"
            
            elif game_state == "info":
                if event.key == pygame.K_RETURN: # Press ENTER to start
                    game_state = "world"
                    # Reset player position if needed
                    player_rect.x, player_rect.y = 50, 260

            
            elif not (game_state in  ["chat","title","info"]) and event.key == pygame.K_e:
                npc_name = get_active_npc()
                if npc_name == "Locked_Jerry":
                    print("Jerry is locked.") # Or use a temporary UI popup
                elif npc_name:
                    previous_state = game_state
                    game_state = "chat"
                    current_npc = npc_name
                    player_input = ""
                    if current_npc == "Jerry":
                        all_npc_stats["Jerry"]["personality"] = generate_jerry_personality()
                    # Ensure the NPC has a history list before accessing
                    if "ui_history" not in all_npc_stats[current_npc]:
                        all_npc_stats[current_npc]["ui_history"] = []
                    messages = all_npc_stats[current_npc]["ui_history"]
                    if len(messages) == 0:                   
                        if current_npc == "Krake":
                            messages.append(f"{current_npc}: Yo, what's up? You that dude with the skelly? SWEET")
                        elif current_npc == "Meridian":
                            messages.append(f"{current_npc}: Greetings, seeker of knowledge. How can we impart wisdom upon your skeletal friend?")
                        elif current_npc == "Atlas":
                            messages.append(f"{current_npc}: Hail, aspiring warrior, I do not discriminate against your creation. We will make them strong")

            elif game_state == "chat":
                if event.key == pygame.K_ESCAPE:
                    game_state = previous_state
                elif event.key == pygame.K_BACKSPACE:
                    player_input = player_input[:-1]
                elif event.key == pygame.K_RETURN and player_input.strip() != "":
                    # --- JERRY BRAIN UPDATE ---
                    if current_npc == "Jerry":
                        all_npc_stats["Jerry"]["personality"] = generate_jerry_personality()
                    
                    # 1. Add to UI
                    messages.append(f"> {player_input}")
                    
                    # 2. Get AI Reply
                    raw_ai_reply = get_llm_response(player_input, current_npc)
                    clean_text = process_npc_reply(raw_ai_reply, current_npc)
                    
                    # 3. Save to AI Memory
                    stats = all_npc_stats[current_npc]
                    stats["chat_history"].append({"role": "user", "content": player_input})
                    stats["chat_history"].append({"role": "assistant", "content": clean_text})
                    
                    # 4. Increment Jerry's Message Count
                    if current_npc == "Jerry":
                        all_npc_stats["Jerry"]["message_count"] += 1
                    
                    # 5. Display NPC reply
                    messages.append(f"{current_npc}: {clean_text}")
                    player_input = ""
                else:
                    if event.unicode.isprintable() and event.unicode != "":
                        player_input += event.unicode
            elif game_state == "assessment":
                if event.key == pygame.K_ESCAPE:
                    game_state = "chat"


        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == "chat" and current_npc == "Jerry":
                # Ensure the count is met
                if all_npc_stats["Jerry"]["message_count"] >= 10:
                    mouse_pos = event.pos
                    
                    # This MUST match the coordinates in draw_chat
                    button_rect = pygame.Rect(750, 20, 230, 60)
                    
                    if button_rect.collidepoint(mouse_pos):
                        get_final_assessment() 
                        game_state = "assessment"
                        draw_assessment_screen()

    # World Updates
    map_states = ["world", "connect", "desert", "mountain"]
    if game_state in map_states:
        keys = pygame.key.get_pressed()
        handle_movement(keys)
        check_transitions()

    # Drawing
    if game_state == "chat":
        # CALL THE FUNCTION HERE:
        draw_chat(current_npc, messages, player_input)
    else:
        # Draw dynamic backgrounds
       # Drawing Section
        if game_state == "title":
            draw_title_screen()
        elif game_state == "info":
            draw_info_panel()
        elif game_state == "assessment":
            draw_assessment_screen()
        else:
            draw_world(game_state)
            screen.blit(player_sprites[0], player_rect)

        # Interaction Prompt
        active_npc = get_active_npc()
        if active_npc:
            # Determine which RECT to use for the prompt position
            target_rect = None
            if active_npc == "Locked_Jerry" or active_npc == "Jerry":
                target_rect = world_npc_rect
            elif active_npc == "Krake":
                target_rect = cool_npc_rect
            elif active_npc == "Meridian":
                target_rect = intel_npc_rect
            elif active_npc == "Atlas":
                target_rect = strength_npc_rect
            
            # Draw the prompt above the NPC's head instead of the player's
            if active_npc == "Locked_Jerry":
                prompt_text = "Jerry hasn't been taught any skills from the Masters!"
                text_color = (200, 200, 200)
            else:
                prompt_text = f"Press E to talk to {active_npc}"
                text_color = (255, 255, 255)

            # 2. Determine target rect for positioning
            target_rect = None
            if active_npc in ["Locked_Jerry", "Jerry"]: target_rect = world_npc_rect
            elif active_npc == "Krake": target_rect = cool_npc_rect
            elif active_npc == "Meridian": target_rect = intel_npc_rect
            elif active_npc == "Atlas": target_rect = strength_npc_rect

            if target_rect:
                #Calculate Bubble Size based on Text
                text_surf = font.render(prompt_text, True, text_color)
                text_rect = text_surf.get_rect()
                
                # Center the bubble above the NPC
                bubble_padding = 10
                bubble_rect = pygame.Rect(0, 0, text_rect.width + (bubble_padding * 2), text_rect.height + (bubble_padding * 2))
                bubble_rect.centerx = target_rect.centerx
                bubble_rect.bottom = target_rect.top - 10
                
                # Draw the Bubble (Shadow, then Box, then Pointer)
                # Shadow
                pygame.draw.rect(screen, (20, 20, 20), (bubble_rect.x + 2, bubble_rect.y + 2, bubble_rect.w, bubble_rect.h), border_radius=8)
                # Main Box (Dark gray background)
                pygame.draw.rect(screen, (50, 50, 50), bubble_rect, border_radius=8)
                # Border (Light gray)
                pygame.draw.rect(screen, (150, 150, 150), bubble_rect, width=2, border_radius=8)
                
                # Draw the Pointer (The little triangle at the bottom)
                pointer_points = [
                    (bubble_rect.centerx - 8, bubble_rect.bottom),
                    (bubble_rect.centerx + 8, bubble_rect.bottom),
                    (bubble_rect.centerx, bubble_rect.bottom + 8)
                ]
                pygame.draw.polygon(screen, (50, 50, 50), pointer_points)
                pygame.draw.lines(screen, (150, 150, 150), False, [pointer_points[0], pointer_points[2], pointer_points[1]], 2)

                # 6. Blit the Text
                screen.blit(text_surf, (bubble_rect.x + bubble_padding, bubble_rect.y + bubble_padding))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()