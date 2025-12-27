def generate_sky_description(
    location,
    date,
    time,
    moon_phase,
    moon_visibility,
    moon_brightness,
    visible_planets,
    cloud_cover,
):
    planets_text = ", ".join(visible_planets) if visible_planets else "no major planets"

    # Visibility meaning text
    if moon_visibility == "Below horizon":
        moon_sentence = "The Moon is currently below the horizon and not visible."
    elif moon_visibility == "Cloud obscured":
        moon_sentence = "The Moon is above the horizon, but cloud cover is obscuring visibility."
    else:
        moon_sentence = "The Moon is clearly visible in the night sky."

    # Cloud interpretation
    if cloud_cover < 20:
            sky_condition = "clear and suitable for sky observation"
    elif cloud_cover < 50:
            sky_condition = "partly cloudy with moderate viewing conditions"
    else:
            sky_condition = "heavily clouded, limiting sky visibility"

    description = f"""
📍 **Location:** {location}  
🕒 **Time:** {time.strftime("%I:%M %p")}  
📅 **Date:** {date.strftime("%d %B %Y")}

The sky tonight is **{sky_condition}**.

🌙 The Moon is in **{moon_phase}** phase with approximately **{moon_brightness:.1f}% illumination**.  
{moon_sentence}

🪐 Visible planets at this time include **{planets_text}**.

✨ Overall, this moment in the sky reflects a calm celestial scene,
with subtle atmospheric variations influencing visibility.
"""

    return description
