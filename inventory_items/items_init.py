
# Define starting IDs for generation.
ITEM_ID_START_COUNTER = 0
ROOM_ID_START_COUNTER = 1 

empty_lab={
            # --- Inventory/House State ---
            "next_item_id": ITEM_ID_START_COUNTER,
            "next_room_id": ROOM_ID_START_COUNTER,
            "current_room_id": 0, # Default starting room ID (must match one below)
            "rooms": [
                {
                    "name": "lab_room",
                    "id": 0,
                    "image": "lab_room",
                    "room_types": ["ALIFE_research"],
                    "music": "white_room",
                    "descriptions": {
    "late night": [
        "A modern laboratory dedicated to A-Life research. The lab is quiet at this late hour.",
        "The light in here is of a deep blue tone, casting long shadows."
    ],
    "early morning": [
        "The lab is just beginning to stir, with a faint hum of machinery.",
        "A cool, crisp light filters through the blinds."
    ],
    "morning": [
        "Activity in the lab is picking up, researchers are at their stations.",
        "Bright, natural light fills the room."
    ],
    "noon": [
        "The lab is bustling with activity.",
        "The overhead lights are at their brightest."
    ],
    "afternoon": [
        "The afternoon slump seems to have hit, some researchers are taking a break.",
        "The blue light feels a bit softer now."
    ],
    "late afternoon": [
        "The lab is starting to wind down, but experiments are still running.",
        "The light outside is beginning to dim, contrasting with the lab's blue glow."
    ],
    "night": [
        "Only a few dedicated researchers remain, the lab is peaceful.",
        "The deep blue light dominates, creating an atmospheric calm."
    ]
},
                    "items": []
                }
            ],
            "inventory": [],
            # --- Emote State (NEW) ---
            "current_emote": "neutral",
            "possible_emotes": {
                "neutral": "I'm feeling calm and attentive.",
                "happy": "I'm feeling cheerful and optimistic.",
                "sad": "I'm feeling down.",
                "confused": "I'm unsure or puzzled.",
                "excited": "I'm enthusiastic and eager.",
                "thinking": "I'm processing information or contemplating.",
                "angry": "I'm feeling frustrated or upset."
            },
            # --- End Emote State ---

            ## -- health state -- ##
                "stats": {
                "fullness": 200.0,
                "hydration": 200.0,
                "energy": 200.0
            },
    # --- End Stats State -

    # --- NEW: Pet Theme Color Configuration ---
    "is_color_configured": False, # Flag to indicate if the one-time setup is done
    "pet_theme_color": [100, 255, 100], # Default color (green), stored as list for JSON
    "steps": 0
    # --- End Pet Theme Color ---
            # --- End Stats State -
        }
        # --- End of override ---






base_state={
            # --- Inventory/House State ---
            "next_item_id": ITEM_ID_START_COUNTER,
            "next_room_id": ROOM_ID_START_COUNTER,
            "current_room_id": 0, # Default starting room ID (must match one below)
            "rooms": [
    {
        "name": "living_room",
        "image": "living_room",
        "room_types": [
            "living_room"
        ],
        "music": "living_room",
        "descriptions": {
            "late night": [
                "The living room is wrapped in darkness, save for the faint flicker of a dying fire casting soft shadows across plush cushions.",
                "A quiet stillness pervades, the room beneath the moonlight filtering through the curtains."
            ],
            "early morning": [
                "Pale dawn light streams through sheer curtains, gently illuminating the worn fabric of the cozy armchairs.",
                "The scent of fresh coffee mingles with soft morning quiet, promising a peaceful start to the day in the comforting space."
            ],
            "morning": [
                "Sunlight pours into the room, warming the overstuffed sofa and highlighting scattered blankets.",
                "Birdsong drifts through an open window as the living room awakens, full of gentle light and welcoming warmth."
            ],
            "noon": [
                "Bright midday light floods the space, enlivening the rich wood tones and plush textures with vivid clarity.",
                "The room hums softly with midday energy, bathed in sunshine and alive with a subtle bustle."
            ],
            "afternoon": [
                "Soft shadows lengthen as the afternoon sun filters through leafy branches outside, draping the living room in a golden glow.",
                "A comfortable nook beckons for rest, where warm light dances across cushions and carpets."
            ],
            "late afternoon": [
                "The setting sun casts a warm amber hue, deepening the rich colors of the cozy furnishings.",
                "A peaceful calm settles as the day wanes, the room cocooned in fading light and gentle quiet."
            ],
            "night": [
                "The living room glows warmly under the soft light of a table lamp, a sanctuary against the dark outside.",
                "Firelight flickers, casting comforting shadows as the room embraces stillness and the hush of night."
            ]
        },
                    "items": [
                {
                    "name": "sofa",
                    "descriptions": [
                        "A large, plush sofa, perfect for lounging."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "window",
                    "descriptions": [
                        "A large, window, it has soft white curtains.",
                        "The world outside looks a bit blurry"
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "TV",
                    "descriptions": [
                        "A flat TV, it seems to always be playing something",
                        "It plays whatever it wants"
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "remote_control",
                    "descriptions": [
                        "A universal remote control, slightly sticky."
                    ],
                    "static": False,
                    "type": ["tool"]
                },
                {
                    "name": "coffee_table",
                    "descriptions": [
                        "A sturdy wooden coffee table."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "bowl_of_nuts",
                    "descriptions": [
                        "A small ceramic bowl filled with mixed nuts."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 5,
                        "hydration": -2,
                        "energy": 8
                    },
                    "effects": [
                        "A satisfying crunch.",
                        "You feel a slight energy boost."
                    ]
                },
                {
                    "name": "mystery_novel",
                    "descriptions": [
                        "A paperback novel with a intriguing cover."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": [
                        {
                            "title": "The Gathering Storm",
                            "content": "The rain lashed against the windows as Detective Miles received the anonymous call, the voice on the other end ragged with fear. \"He's gone... they took him,\" the caller choked out before the line went dead, leaving only the sound of distant thunder and Miles's own racing heart. This wasn't the typical petty crime; this felt darker, colder, like the storm brewing outside."
                        },
                        {
                            "title": "A Cryptic Clue",
                            "content": "Beneath the overturned vase, a small, folded piece of paper lay hidden, damp but the ink still legible. It wasn't a name or an address, but a series of symbols and numbers that meant nothing to Miles initially. Yet, there was a deliberate quality to its placement, a message clearly intended to be found, if only by the right eyes."
                        },
                        {
                            "title": "Whispers in the Alley",
                            "content": "Miles followed the breadcrumbs from the cryptic note to a grimy alley behind the old docks, the air thick with the smell of salt and decay. A shadowy figure lingered near overflowing bins, startled by Miles's approach. \"You askin' 'bout the professor?\" the figure rasped, eyes darting nervously. \"Saw him with a couple of rough types, headed towards the abandoned warehouse last night. Looked like they weren't goin' for tea.\"\n\nThe figure, a dockworker named Silas with a reputation for seeing things he shouldn't, reluctantly shared more details. He mentioned a distinctive symbol one of the men wore \u2013 a coiled serpent \u2013 and the specific time they'd passed by. Silas's fear was palpable, whispering that these weren't local thugs, but 'outsiders' who didn't ask questions, they just took what they wanted. His information, though sparse, gave Miles a concrete direction and a chilling confirmation that the professor's disappearance was no accident."
                        },
                        {
                            "title": "The Warehouse's Secret",
                            "content": "The abandoned warehouse loomed by the water, its broken windows like vacant eyes staring out at the choppy sea. Inside, dust motes danced in the few shafts of light filtering through the gaps in the roof. The air was cold, stagnant, and heavy with the scent of mildew and something else... something metallic and faint. Careful footsteps echoed in the vast space as Miles searched, finding scattered crates and forgotten machinery, but no immediate sign of the professor.\n\nHowever, a section of the concrete floor near the back wall seemed newer, less stained than the rest. Prying at a small crack revealed that it wasn't solid concrete, but a cleverly disguised hatch. Beneath it lay not a storage space, but a narrow, descending stairwell leading into absolute darkness, the metallic scent much stronger now. The warehouse wasn't just a drop-off point; it was a gateway to somewhere hidden beneath."
                        }
                    ]
                },
                {
                    "name": "woolen_blanket",
                    "descriptions": [
                        "A soft, warm woolen blanket."
                    ],
                    "static": False,
                    "type": ["misc"]
                },
                {
                    "name": "decorative_vase",
                    "descriptions": [
                        "A tall, ceramic vase with an abstract pattern."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "old_magazine",
                    "descriptions": [
                        "A slightly outdated magazine with ripped pages."
                    ],
                    "static": False,
                    "type": ["misc"]
                }
            ]
    },
    {
        "name": "kitchen",
        "image": "kitchen",
        "room_types": [
            "kitchen"
        ],
        "music": "kitchen",
        "descriptions": {
            "late night": [
                "The kitchen is hushed under the moonlight, stainless steel surfaces reflecting faint city lights through the window.",
                "A soft breeze stirs the curtains, carrying faint whispers of spices left from dinner."
            ],
            "early morning": [
                "First light filters softly through the window, casting a gentle glow on gleaming appliances.",
                "The cool morning air brings a fresh spice scent, mingling with the crisp cleanliness of the kitchen."
            ],
            "morning": [
                "Sunlight pours in warmly, igniting sparkle on stainless steel and brightening the cozy kitchen nook.",
                "The air feels fresh, with a lingering hint of spices from breakfast preparations."
            ],
            "noon": [
                "Bright midday rays flood the kitchen, turning every surface into shining metal and glass.",
                "A gentle wind drifts through the open window, melding the spicy aroma with fresh daytime air."
            ],
            "afternoon": [
                "The kitchen is lively with soft ambient light, the clean gleaming surfaces.",
                "A faint spice scent lingers as the breeze dances through the window over the sink."
            ],
            "late afternoon": [
                "Golden light bathes the kitchen, warming the stainless steel to a gentle glow.",
                "The air feels cozy, with drifting scents of spices and fresh breeze mixing in the quiet room."
            ],
            "night": [
                "Dimmed lights create a calm ambiance, reflecting subtly on polished steel appliances.",
                "The window frames the dark outdoors as a soft wind carries faint spice aromas inside."
            ]
        },
                    "items": [
                {
                    "name": "apple",
                    "descriptions": [
                        "A fresh, shiny red apple."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 10,
                        "hydration": 5,
                        "energy": 5
                    },
                    "effects": [
                        "You feel a little healthier.",
                        "A sweet taste lingers."
                    ]
                },
                {
                    "name": "kitchen_knife",
                    "descriptions": [
                        "A sharp chef's knife on a magnetic strip."
                    ],
                    "static": False,
                    "type": ["tool"]
                },
                {
                    "name": "loaf_of_bread",
                    "descriptions": [
                        "A crusty, fresh loaf of bread."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 25,
                        "hydration": -5,
                        "energy": 10
                    },
                    "effects": [
                        "Fills you up nicely.",
                        "A satisfyingly simple taste."
                    ]
                },
                {
                    "name": "wedge_of_cheese",
                    "descriptions": [
                        "A tasty-looking wedge of cheddar cheese."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 20,
                        "hydration": -1,
                        "energy": 12
                    },
                    "effects": [
                        "Rich and flavorful.",
                        "You feel sustained."
                    ]
                },
                {
                    "name": "can_of_soup",
                    "descriptions": [
                        "A simple can of tomato soup."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 20,
                        "hydration": 5,
                        "energy": 15
                    },
                    "effects": [
                        "Warms you up.",
                        "Slightly metallic taste from the can?"
                    ]
                },
                {
                    "name": "bottle_of_water",
                    "descriptions": [
                        "A clear plastic bottle of clean water."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 0,
                        "hydration": 40,
                        "energy": 5
                    },
                    "effects": [
                        "Refreshing.",
                        "Quenches your thirst."
                    ]
                },
                {
                    "name": "coffee_grounds",
                    "descriptions": [
                        "A bag of aromatic coffee grounds."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 1,
                        "hydration": -5,
                        "energy": 20
                    },
                    "effects": [
                        "Very bitter!",
                        "You feel a caffeine kick."
                    ]
                },
                {
                    "name": "spatula",
                    "descriptions": [
                        "A standard rubber spatula."
                    ],
                    "static": False,
                    "type": ["tool"]
                },
                {
                    "name": "saucepan",
                    "descriptions": [
                        "A medium-sized metal saucepan."
                    ],
                    "static": False,
                    "type": ["tool"]
                },
                {
                    "name": "cookbook",
                    "descriptions": [
                        "A thick book titled 'Mastering the Culinary Arts'."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": [
                        {
                            "title": "Soups and Stews",
                            "content": "Learn the basics of creating hearty, warming meals that nourish the body and soul. Soups typically involve simmering ingredients in a liquid base, while stews are thicker, featuring larger pieces of meat and vegetables cooked slowly in less liquid. Both techniques are incredibly versatile, allowing you to utilize seasonal ingredients and leftovers efficiently.\n\nMastering a few fundamental stocks \u2013 chicken, beef, or vegetable \u2013 is key to flavorful soups and stews. Pay attention to simmering times to ensure ingredients are tender but not mushy, and learn how to properly thicken a stew using methods like a roux, reduction, or starches. A well-made soup or stew can be a meal unto itself, perfect for cold evenings."
                        },
                        {
                            "title": "Baking Bread",
                            "content": "From sourdough starters to simple yeast loaves, unlock the secrets of baking your own nourishing bread. The magic lies in understanding the interaction between flour, water, yeast (or wild cultures), and time. Basic yeast bread requires kneading to develop gluten structure, allowing the dough to rise into a light, airy loaf when baked correctly.\n\nExplore different flours \u2013 wheat, rye, barley \u2013 and experiment with additions like herbs, cheese, or seeds to create a variety of textures and flavors. Perfecting baking temperatures and understanding proofing times are essential steps to achieving that golden crust and soft interior. The smell of fresh-baked bread is one of life's simple, yet profound, pleasures."
                        },
                        {
                            "title": "Desserts",
                            "content": "Indulge your sweet tooth with our collection of cakes, pies, and pastries, ranging from simple fruit tarts to elaborate layered creations. Understanding the role of sugar, fats, and leavening agents is crucial for achieving the desired texture, whether it's a tender crumb, a flaky crust, or a rich custard. Precision in measuring ingredients is often more critical in baking than in savory cooking.\n\nExplore different methods for making pastries, such as the delicate folding required for puff pastry or the simple rubbing-in method for shortcrust. Learn how to create smooth glazes, stable frostings, and vibrant fruit fillings. Baking desserts is a rewarding process that allows for both technical skill and creative expression."
                        },
                        {
                            "title": "Roasting and Braising",
                            "content": "Master the art of transforming cuts of meat and vegetables through controlled heat. Roasting involves cooking with dry heat in an oven or over an open fire, typically at higher temperatures, which is ideal for tender cuts like joints or poultry, creating a delicious browned exterior and succulent interior. Braising, conversely, uses moist heat; the ingredient is often seared first, then cooked slowly in a small amount of liquid in a covered pot, perfect for tougher cuts that become meltingly tender over time.\n\nFor roasting, proper seasoning, basting, and allowing the meat to rest after cooking are key to retaining juices. For braising, selecting the right liquid base (stock, wine, or cider), ensuring the pot is tightly covered to trap steam, and maintaining a low, consistent temperature are paramount. Both techniques can be applied to vegetables as well, yielding intensely flavorful and tender results quite different from other cooking methods."
                        },
                        {
                            "title": "Preserves and Pickles",
                            "content": "Learn how to extend the bounty of the harvest and add vibrant flavors to your larder by preserving fruits and vegetables. Making preserves, like jams, jellies, and chutneys, typically involves cooking fruit with sugar, which acts as a preservative while concentrating flavor and achieving a spreadable consistency. Pickling involves submerging ingredients in an acidic solution, usually vinegar or a salty brine, to inhibit spoilage and impart a tangy flavor.\n\nSuccessfully creating preserves and pickles relies on careful preparation of the ingredients, accurate measurement of sugar or salt/vinegar ratios, and rigorous attention to sterilization to ensure food safety and longevity. Properly sealed jars of homemade preserves and pickles can last for months, providing a taste of peak freshness long after the season has passed and adding bright notes to meals throughout the year."
                        }
                    ]
                }
            ]
    },
    {
        "name": "library",
        "image": "library",
        "room_types": [
            "library"
        ],
        "music": "library",
        "descriptions": {
            "late night": [
                "The library lies in profound silence, bathed in the gentle glow of a single reading lamp, shadows dancing across towering shelves.",
                "The scent of aged paper deepens as moonlight filters through the high windows, wrapping the room in a quiet, contemplative hush."
            ],
            "early morning": [
                "Soft dawn light spills softly over rows of leather-bound tomes, the air fresh yet rich with the musk of history.",
                "A gentle hush lingers, broken only by the faint rustle of pages as the library begins to stir from slumber."
            ],
            "morning": [
                "Sunlight floods the room, illuminating the golden spinesbeneath the soaring shelves.",
                "Warm rays coax a cozy ambiance, where the comforting scent of old books welcomes early visitors."
            ],
            "noon": [
                "Bright midday light fills the library, revealing every crease and dust mote in the air, alive and welcoming.",
                "The peaceful room hums gently with the subtle movements of readers, wrapped in the comforting aroma of aged parchment."
            ],
            "afternoon": [
                "Late afternoon sun casts elongated shadows between the aisles, adding depth to the hushed, cozy space.",
                "The warmth from the sinking sun complements the rich leather and paper scents."
            ],
            "late afternoon": [
                "Golden light intensifies as day wanes, highlighting the intricate textures of bindings and polished wood.",
                "A serene calm envelops the library, bathed in a soft amber glow, perfect for quiet reflection."
            ],
            "night": [
                "Darkness outside deepens the library\u2019s glow, where lamps emit a warm, intimate light amid endless stories.",
                "The quiet hush is profound, every whispered turn of a page echoing softly beneath the high ceiling."
            ]
        },
        "items": [
                {
                    "name": "ancient_tome",
                    "descriptions": [
                        "A dusty, heavy tome bound in weathered leather."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": [
                        {
                            "title": "Origins of the Void",
                            "content": "Long ago, before the stars were born, there was only the silent, formless void, an infinite expanse of nothingness pregnant with unrealized potential. This was not darkness as we know it, but an absolute absence of light, sound, and substance, where the very concepts of time and space held no meaning. It is said that the first stirrings of existence were but infinitesimal ripples upon this boundless, primordial ocean of non-being.\n\nThe tome hints that the material realm, with all its chaotic energy and vibrant life, is but a thin membrane stretched over the surface of this eternal nullity. Glimpses of the Void can sometimes be perceived in places of utter desolation or through certain forbidden practices, and its chilling emptiness is a constant reminder of the fragile, temporary nature of reality."
                        },
                        {
                            "title": "Whispers of the Future",
                            "content": "Foretellings of events yet to unfold, written in a script that shifts before your eyes, defy linear time as understood by mortals. These are not simple predictions but echoes from the future, vibrating backward through the fragile fabric of causality. Reading them requires not just understanding the mutable glyphs, but sensing the resonance of probabilities and potential outcomes, a practice fraught with peril as it can blur the lines between what is and what might be.\n\nThe whispers are rarely clear, often contradictory, and deeply unsettling, speaking of great cosmic shifts, the alignment of distant, unknown stars, and the slow erosion of reality by unseen forces. Attempting to decipher these future echoes can attract unwanted attention from entities dwelling outside of time, who view such scrying as an intrusion and may seek to silence the reader permanently."
                        },
                        {
                            "title": "The Elder Signs",
                            "content": "Illustrations and descriptions of symbols said to ward off or beckon entities from beyond the veil, these signs are potent conductors of intent and anchors in the non-Euclidean spaces they represent. They are not mere drawings, but diagrams of cosmic forces and pathways, each line and curve imbued with ancient, possibly dangerous, power. Some signs are protective, meant to form barriers against intrusions from the Void, while others are keys, designed to open gates or attract the notice of beings best left undisturbed.\n\nUsing the Elder Signs requires precise execution and a deep understanding of their True meaning, lest one invite disaster instead of protection or communication. Misdrawn or misunderstood, they can backfire horribly, drawing unwelcome attention, causing localized distortions in reality, or even inflicting madness upon the one who invokes them. Caution and reverence are paramount when dealing with these ancient glyphs."
                        },
                        {
                            "title": "The Architects of Stillness",
                            "content": "Beyond the reaches of the material cosmos, in the tranquil spaces where even light refuses to tread, reside entities known only as the Architects of Stillness. They are not born of matter or energy, but are fundamental aspects of the non-existent, dwelling in absolute quietude. Their forms, if they can be said to have forms, are described as impossible geometries or simply the profound absence of anything else, chilling the soul of any who perceive them.\n\nThe tome postulates that these Architects are passively, perhaps unknowingly, influencing the edges of reality, their sheer stillness imposing moments of inexplicable silence or dread in the noisiest corners of existence. Attempts to contact them are futile, as sound and thought are abhorrent to their nature. Instead, their influence is felt as a growing sense of emptiness and futility that can creep into the minds of sensitive beings, a slow dissolution towards their own state of non-being."
                        },
                        {
                            "title": "The Gateways of Flesh",
                            "content": "This chapter details forbidden rituals centered on the manipulation of the physical form, not for mundane power, but as keys to unlock passages between realms. These practices are gruesome, involving precise excisions, unnatural contortions, and the mapping of cosmic alignments onto the suffering body. The goal is not transformation, but the creation of a living, screaming resonance that momentarily thins the veil separating the material world from the Void.\n\nThe tome warns that these are not prayers or offerings, but violent acts of defiance against the natural order, forcing reality to buckle. The sites of such rituals are forever tainted, vibrating with residual psychic and physical agony. Those who attempt to construct these 'Gateways of Flesh' risk not only their sanity and life, but also the integrity of existence around them, attracting the ravenous attention of whatever horrors may lurk just beyond the threshold."
                        }
                    ]
                },
                {
                    "name": "comfy_armchair",
                    "descriptions": [
                        "A large, upholstered armchair, perfect for reading."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "reading_lamp",
                    "descriptions": [
                        "A brass reading lamp next to the armchair."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "journal_with_pen",
                    "descriptions": [
                        "A blank leather-bound journal with a pen tucked into its strap."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": []
                },
                {
                    "name": "history_of_the_realm",
                    "descriptions": [
                        "A comprehensive history book detailing local events."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": [
                        {
                            "title": "The Founding",
                            "content": "The first stones were laid in the year of the Great Stag, when Chieftain Eldrin Ironhand united the scattered tribes of the valley. Facing constant threats from the northern raiders, Eldrin envisioned a fortified settlement, a place where his people could thrive and defend themselves from external aggression. This pivotal moment marked the beginning of recorded history for the realm, establishing the initial boundaries and laying the groundwork for its future development."
                        },
                        {
                            "title": "The Silver War",
                            "content": "A bloody conflict erupted over control of the eastern mines, resources vital to the realm's economy and military strength. Lasting for five brutal years, the war pitted regional lords against the central authority, fueled by greed and ancient rivalries. Villages were razed, trade routes disrupted, and countless lives were lost on both sides of the conflict."
                        },
                        {
                            "title": "Modern Governance",
                            "content": "The current council was established after the treaty of Oakhaven, a fragile peace agreement brokered in the aftermath of the Succession Crisis. This council, composed of representatives from key noble houses and merchant guilds, aims to provide a more stable and equitable form of leadership than the single monarch it replaced. Their decisions guide policy on trade, defense, and justice within the realm's borders."
                        },
                        {
                            "title": "The Great Plague",
                            "content": "In the Year of the Weeping Star, a devastating plague swept across the land, originating in the crowded port cities and quickly spreading inland. The disease claimed nearly a third of the population, leaving villages deserted and throwing the social order into chaos. Healers and alchemists worked tirelessly, but few remedies proved effective against the relentless malady."
                        },
                        {
                            "title": "The Age of Exploration",
                            "content": "Following the plague's retreat, a period of renewed vigor led to the Age of Exploration. Brave captains sailed the uncharted waters of the Sunset Sea, seeking new trade routes and lands. These voyages brought back exotic goods, strange knowledge, and sometimes, new conflicts with the peoples encountered beyond the known world. Mapmakers became invaluable as the realm's understanding of the globe expanded significantly."
                        },
                        {
                            "title": "The Ironwood Treaties",
                            "content": "Centuries after the founding, a series of treaties known as the Ironwood Treaties solidified the realm's borders and established long-lasting alliances with neighboring kingdoms. These agreements, hammered out over decades of negotiation and minor skirmishes, defined spheres of influence and mutual defense pacts. While not entirely eliminating border disputes, they ushered in an era of relative peace and increased diplomatic ties."
                        }
                    ]
                },
                {
                    "name": "atlas_of_the_world",
                    "descriptions": [
                        "A large, detailed atlas with maps of various regions."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": [
                        {
                            "title": "The Western Continents",
                            "content": "Explore the vast lands beyond the Sunset Sea... (Detailed map follows)\n\nThese continents are home to diverse empires, soaring mountain ranges, and deep, ancient forests. From the temperate northern coasts to the sun-scorched southern plains, life thrives in countless forms and civilizations rise and fall like the tides. Studying the terrain and key locations on the map is vital for understanding the history and power dynamics of this dominant landmass."
                        },
                        {
                            "title": "The Eastern Isles",
                            "content": "A chain of volcanic islands known for their unique flora and fauna... (Detailed map follows)\n\nStretching across the Eastern Ocean, these islands range from steaming volcanic peaks to lush, secluded lagoons. Many species here are found nowhere else in the world, adapted to the islands' isolated ecosystems and frequent seismic activity. Navigating the treacherous currents between islands and identifying safe harbors requires careful consultation of the included maritime charts."
                        },
                        {
                            "title": "The Northern Reaches",
                            "content": "Journey into the lands of ice and frost... (Detailed map follows)\n\nFar beyond the temperate zones lies the unforgiving expanse of the Northern Reaches. This territory is dominated by immense glaciers, frozen tundras, and jagged fjords that carve into a desolate coastline. Survival here is a constant battle against the elements, with long, dark winters and biting winds sweeping across the frozen plains."
                        },
                        {
                            "title": "The Shifting Sands",
                            "content": "Uncover the secrets buried beneath the dunes... (Detailed map follows)\n\nTo the south, stretching further than the eye can see, is the vast and deadly territory known as the Shifting Sands. This immense desert is a sea of dunes, where landmarks are few and water is a precious rarity. Ancient ruins are said to lie half-buried beneath the sand, remnants of civilizations claimed by the scorching heat and endless drought."
                        },
                        {
                            "title": "The Underworld Depths",
                            "content": "Descend into the caverns below... (Detailed map follows)\n\nNot all lands exist under the sun; beneath the surface lies a complex network of caverns, tunnels, and vast subterranean lakes known collectively as the Underworld Depths. Home to unique geological formations and species adapted to eternal darkness, this region presents an entirely different challenge for explorers. The map details known primary routes and major chambers, though countless unexplored passages remain hidden."
                        },
                        {
                            "title": "The Sky Islands",
                            "content": "Ascend to the floating landmasses... (Detailed map follows)\n\nA truly unique phenomenon are the Sky Islands, great chunks of land that mysteriously float high above the surface world. These islands possess their own peculiar climates and ecosystems, some supporting strange flora and fauna, others containing rare minerals drawn upwards from deep within the earth. The map indicates approximate positions and known stable platforms, though movement and altitude can vary."
                        }
                    ]
                },
                {
                    "name": "poetry_anthology",
                    "descriptions": [
                        "A collection of modern and contemporary poems."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": [
                        {
                            "title": "City Scratches",
                            "content": "Cobblestones gleam, slick with rain,\ncarrying the tired lamplight down drain.\nGhost of footsteps echo in the narrow space,\na forgotten scent, a hurried pace.\n\nHigh window, a single yellow square,\nholds somebody breathing the damp air.\nThe city breathes, a low, wet sigh,\nbeneath a sky the color of a bruised eye."
                        },
                        {
                            "title": "Root-Bound Silence",
                            "content": "Beneath the ancient oak's spread,\nwhere tangled roots make a tangled bed,\nthe air hangs thick, tasting of earth and mold,\nsecrets the silent stones have held.\n\nA single dewdrop clings to a spider's thread,\nreflecting a sunbeam, barely shed.\nNo birdsong here, no rustling leaf,\njust the deep, slow breath of green relief."
                        },
                        {
                            "title": "The Hum Behind the Eyes",
                            "content": "The world outside is sharp, defined,\nbut inside the hum is hard to find.\nA low vibration, behind the bone,\na radio frequency, tuned to the unknown.\n\nSometimes it whispers, sometimes it screams,\na static haze over waking dreams.\nIs it my own pulse, or something vast,\na message from a future or the past?"
                        }
                    ]
                },
                {
                    "name": "botany_guide",
                    "descriptions": [
                        "A guide to identifying local plants and their uses."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": [
                        {
                            "title": "Identifying Common Herbs",
                            "content": "Learn to distinguish between Feverfew, Comfrey, and Valerian, three of the most frequently encountered and utilized herbs in the realm. Feverfew is recognized by its small, daisy-like flowers and pungent scent, commonly used for headaches and fevers. Comfrey, with its large, hairy leaves and bell-shaped flowers, is renowned for its ability to aid bone and tissue healing, though internal use is cautioned against.\n\nValerian is identified by its strong, distinct odor and clusters of small pink or white flowers atop a tall stem; it is a potent relaxant and sleep aid. Mastering the identification of these foundational herbs is crucial for any aspiring healer or traveler needing basic medicinal knowledge in the wild."
                        },
                        {
                            "title": "Edible Wild Plants",
                            "content": "A guide to foraging safely for berries, roots, and leaves that can provide sustenance when other food sources are scarce. Important examples include the Sweetroot, a tuber found in moist soil identifiable by its broad leaves, which is nutritious when roasted. Wild Greens, such as those resembling nettles but lacking their sting, can be boiled to remove bitterness and provide essential vitamins.\n\nAlways positively identify a plant multiple times before consuming it, as many edible species have poisonous look-alikes. Pay attention to leaf shape, stem structure, growth location, and any flowers or fruits. When in doubt, do not eat it; even small amounts of certain plants can be deadly."
                        },
                        {
                            "title": "Poisonous Species",
                            "content": "Crucial information on plants to avoid at all costs, as ingestion or even contact can cause severe harm or death. The Deathcap Mushroom, while not a plant, is often mistaken for edible fungi and is lethally toxic, identifiable by its white gills, ring on the stem, and volva cup at the base. The Hemlock plant, with its purple-spotted stem and parsley-like leaves, is another highly poisonous species; even a small amount ingested can cause respiratory failure.\n\nLearn the appearance of common irritants like Itchvine, which causes blistering rashes upon contact, and airborne irritants from certain flowering plants that can cause severe allergic reactions. Carrying a small amount of purifying poultice or antidote is advised when traveling through areas known for dangerous flora, and always treat unknown plants with extreme caution."
                        },
                        {
                            "title": "Trees of the Whispering Woods",
                            "content": "The Whispering Woods are dominated by several key tree species, each with distinct characteristics. The Ironwood, named for the incredible density and strength of its timber, is easily recognized by its deeply furrowed, dark bark and broad, persistent leaves. The Moonpetal Birch, on the other hand, has smooth, silver-white bark that peels like paper, and delicate, pale leaves that seem to glow faintly in twilight.\n\nIdentifying these trees is vital for woodcutters and builders; Ironwood is prized for fortifications and weapons, while Moonpetal Birch wood is lighter, easier to work, and often used in fine furniture or carvings. Pay attention to bark texture, leaf shape, and the arrangement of branches, as these are the primary identifiers when the trees are bare in winter."
                        },
                        {
                            "title": "Fungi of the Damp Caves",
                            "content": "The subterranean environments of the Damp Caves host a unique ecosystem dominated by various fungal lifeforms adapted to perpetual darkness. The Glowcap, a bioluminescent mushroom, provides the primary light source in many caverns and is identifiable by its soft blue or green light emanating from the cap's underside. The Stonefoot Fungus, found growing directly on damp rock faces, is tough and rubbery, often serving as a minor food source for cavern dwellers.\n\nWhile many cave fungi are harmless or have specific, often minor, effects, some can be toxic or even explosive if disturbed. Always observe subterranean fungi from a distance before interacting, noting their color, growth pattern, and any unusual emanations or scents. The Glowcap's light is useful for navigation, but caution is advised with less well-documented species."
                        },
                        {
                            "title": "Desert Cacti and Succulents",
                            "content": "Surviving in the harsh environment of the Shifting Sands requires understanding the flora adapted to extreme drought and heat. Barrel Cacti are common, identifiable by their ribbed, cylindrical shape and formidable spines; their inner pulp can provide a small amount of emergency water when carefully extracted. The Dune Lily, a succulent with thick, fleshy leaves often buried except for the tips, stores water and nutrients underground.\n\nMany desert plants are spiny or possess irritants as defense mechanisms against dehydration and predation. Learn to distinguish edible or useful species from purely defensive ones. The presence of certain succulents can also indicate slightly higher water tables, making them valuable markers for travelers seeking oases or subterranean water sources."
                        }
                    ]
                }
            ]
    },
    {
        "name": "bathroom",
        "image": "bathroom",
        "room_types": [
            "bathroom"
        ],
        "music": "bathroom",
        "descriptions": {
            "late night": [
                "The bathroom is bathed in soft, muted moonlight reflecting off the large mirror, with faint floral scents lingering in the still air.",
                "A quiet, serene space where the humid warmth embraces the calm of the late night."
            ],
            "early morning": [
                "Morning light filters gently through a nearby window, illuminating the tiles as the air carries fresh hints of soap and toothpaste.",
                "The bathroom feels crisp and renewing, the mirror fogged slightly from an early rinse, welcoming the new day."
            ],
            "morning": [
                "Bright sunlight pours in, sparkling on the clean tiles and making the mirror gleam.",
                "The floral scent is fresh and uplifting, blending with the warm, humid air of a busy morning routine."
            ],
            "noon": [
                "The bathroom is filled with clear, natural light that makes the glossy tiles and mirror shine vibrantly.",
                "A moment of calm midday, the air still lightly scented and warmth settling softly around the space."
            ],
            "afternoon": [
                "Sunlight softens, casting gentle shadows on the tiled walls, while the aromatic soap scent lingers pleasantly.",
                "The humid air feels less intense now, the mirror reflecting a cozy, quiet afternoon atmosphere."
            ],
            "late afternoon": [
                "Golden light floods the room, warming the tiles and intensifying the floral aroma amid the fading humidity.",
                "The large mirror glows under the amber hues."
            ],
            "night": [
                "Dim lighting casts subtle reflections in the mirror, mingling with the floral scent in the cool, humid air.",
                "A tranquil retreat where shadows soften the tiled surfaces, wrapping the room in soothing coziness."
            ]
        },
        "items": [
                {
                    "name": "soap_bar",
                    "descriptions": [
                        "A bar of fragrant lavender soap."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 0,
                        "hydration": 5,
                        "energy": 2
                    },
                    "effects": [
                        "You feel fresh and clean.",
                        "The smell is quite pleasant."
                    ]
                },
                {
                    "name": "toothbrush",
                    "descriptions": [
                        "A simple plastic toothbrush."
                    ],
                    "static": False,
                    "type": ["tool"]
                },
                {
                    "name": "tube_of_toothpaste",
                    "descriptions": [
                        "A tube of mint-flavored toothpaste."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 0,
                        "hydration": 8,
                        "energy": 3
                    },
                    "effects": [
                        "Your mouth feels clean and minty.",
                        "A slight tingle."
                    ]
                },
                {
                    "name": "clean_towel",
                    "descriptions": [
                        "A fluffy white towel hanging on a rack."
                    ],
                    "static": False,
                    "type": ["misc"]
                },
                {
                    "name": "medicine_cabinet",
                    "descriptions": [
                        "A metal medicine cabinet mounted on the wall."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "pain_relievers",
                    "descriptions": [
                        "A bottle of common pain relievers."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 0,
                        "hydration": 5,
                        "energy": 20
                    },
                    "effects": [
                        "You feel a dull ache subside.",
                        "A slightly chalky taste."
                    ]
                }
            ]
    },
    {
        "name": "bedroom",
        "image": "bedroom",
        "id": 0,
        "room_types": [
            "bedroom"
        ],
        "music": "bedroom",
        "descriptions": {
            "late night": [
                "The bedroom is cloaked in shadows, the large bed a silent sanctuary beneath the pale moonlight filtering through swaying curtains.",
                "A soft breeze whispers through the curtains, the room wrapped in quiet stillness."
            ],
            "early morning": [
                "A gentle dawn light warms the room, curtains fluttering softly as fresh air drifts in, promising a tranquil start.",
                "First rays peek through the curtains, caressing the cozy bed as the quiet morning breeze stirs the air."
            ],
            "morning": [
                "Sunlight floods the peaceful bedroom, casting playful shadows while the curtains dance softly in the breeze.",
                "The bed basks in warm morning light, the curtains swaying gently, filling the room with calm energy."
            ],
            "noon": [
                "Bright daylight fills the room, warm air moving the curtains lazily as the bed rests in serene quiet.",
                "The bedroom glows with midday sun, the soft breeze gently stirring lightweight curtains around the bed."
            ],
            "afternoon": [
                "The room bathes in a mellow glow, curtains waving gently in the soft afternoon wind, the bed awaiting repose.",
                "Golden afternoon light filters through billowing curtains, settling on the plush bed in peaceful stillness."
            ],
            "late afternoon": [
                "Shadows grow longer as the sun dips, the curtains swaying slowly with a cooling breeze over the cozy bed.",
                "The fading light casts a serene haze, curtains stirring gently, the bed an unchanging haven of calm."
            ],
            "night": [
                "Moonlight spills softly through the curtains, the room hushed and the large bed.",
                "The peaceful bedroom rests under a blanket of night, curtains swaying gently, wrapped in quiet comfort."
            ]
        },
        "items": [
                {
                    "name": "pillow",
                    "descriptions": [
                        "A soft, fluffy pillow on the bed."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "bedside_novel",
                    "descriptions": [
                        "A well-worn novel left open on the nightstand."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": [
                        {
                            "title": "Chapter 1: The Old House",
                            "content": "Once upon a midnight dreary, while I pondered weak and weary, over many a quaint and curious volume of forgotten lore... The old house stood silent on the hill, its windows like vacant eyes staring out over the mist-shrouded valley. Dust motes danced in the sparse moonlight that pierced the grimy panes, illuminating forgotten relics of lives long past. It was here, within its crumbling walls, that the first faint whispers of the adventure began, drawn by an unseen force to the secrets hidden within its foundations."
                        },
                        {
                            "title": "Chapter 2: A Journey Begins",
                            "content": "Across mountains and valleys, through whispering forests and echoing caves, the path stretched out, uncertain but compelling. The protagonist, guided by an instinct older than maps, left the familiar comforts of home behind, setting foot onto ancient trails rumored to lead to places of both wonder and danger. Supplies were few, the journey long, but the pull of the unknown, of destiny, was stronger than any fear."
                        },
                        {
                            "title": "Chapter 3: First Encounters",
                            "content": "The air grew cold as a figure emerged from the mist, their eyes glowing with an otherworldly light that seemed to pierce the very soul. They were neither human nor beast, their form shifting subtly at the edges of vision, cloaked in shadows that defied the morning light. A silence fell, broken only by the protagonist's ragged breath and the distant cry of a hawk overhead, marking this moment as profoundly significant, a meeting outside the bounds of ordinary existence."
                        },
                        {
                            "title": "Chapter 4: The Whisperer's Words",
                            "content": "The figure did not speak with a voice heard by the ears, but with thoughts placed directly into the mind, a cascade of images and feelings that were both alien and strangely familiar. They spoke of balance, of threads woven and unraveled, and of a disruption far older than the mountains themselves. The glowing eyes held an ancient sorrow, hinting at responsibilities vast and terrible, a burden they seemed on the verge of sharing.\n\nThe message was cryptic, filled with riddles of stars and stones, but one command was clear: a specific object, lost to mortal memory, must be found before a certain celestial alignment. The figure imparted a symbol, etched not onto the hand, but into the protagonist's awareness, a mark that would guide the way and perhaps signal their worthiness. Then, as silently as they had appeared, the figure dissolved back into the mist, leaving the traveler alone with impossible knowledge and a daunting task."
                        },
                        {
                            "title": "Chapter 5: A Change in Direction",
                            "content": "The path forward was no longer a simple journey towards a vague destination, but a focused quest with a specific, urgent goal dictated by a being beyond comprehension. The symbol burned faintly in the protagonist's thoughts, a constant reminder of the task. Consulting worn maps and piecing together fragmented legends, it became clear that the object mentioned by the Whisperer was tied to a region far from the original route, a place whispered about only in hushed tones by fearful villagers.\n\nThis new destination lay through territory rumored to be cursed, haunted by lingering energies from ancient conflicts. The cheerful optimism that had fueled the initial journey was replaced by a grim determination. The stakes had been raised immeasurably, and the traveler understood that failure was not merely a personal setback, but potentially a cosmic catastrophe. The journey had truly just begun, leading now into the heart of True peril."
                        }
                    ]
                },
                {
                    "name": "large_bed",
                    "descriptions": [
                        "A large, comfortable bed with clean sheets."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "wardrobe",
                    "descriptions": [
                        "A wooden wardrobe filled with clothes."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "cozy_sweater",
                    "descriptions": [
                        "A thick, knitted sweater."
                    ],
                    "static": False,
                    "type": "armor",
                    "stats_edit": {
                        "energy": 5
                    },
                    "effects": [
                        "You feel warm and snug.",
                        "Blocks a small amount of chill."
                    ]
                },
                {
                    "name": "alarm_clock",
                    "descriptions": [
                        "A digital alarm clock on the nightstand."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "personal_diary",
                    "descriptions": [
                        "A locked diary with a small heart-shaped clasp."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": []
                },
                {
                    "name": "glass_of_water",
                    "descriptions": [
                        "A glass of water on the nightstand."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 2,
                        "hydration": 25,
                        "energy": 3
                    },
                    "effects": [
                        "Refeshing.",
                        "Cool and pure."
                    ]
                }
            ]
    },
    {
        "name": "computer_room",
        "image": "computer_room",
        "room_types": [
            "computer_room"
        ],
        "music": "computer_room",
        "descriptions": {
            "late night": [
                "The room is bathed in the cool glow of monitors, the hum of machines soothing in the stillness of night.",
                "Wires cast tangled shadows as a faint ozone scent lingers, the cozy space alive with quiet electronic murmurs."
            ],
            "early morning": [
                "Soft dawn light filters through blinds onto the cluttered desks, machines buzzing gently as the day begins.",
                "A faint smell of ozone mixes with morning air, the room\u2019s electronics waking up in soft harmony."
            ],
            "morning": [
                "Sunlight streams across tangled wires and screens, lending warmth to the room\u2019s persistent electronic hum.",
                "Monitors flicker with fresh data, the cozy nook alive with the promise of a productive day."
            ],
            "noon": [
                "Bright midday light floods the room, illuminating every wire and screen amidst the steady electronic chorus.",
                "The ozone scent sharpens slightly as machines work steadily under the sunlit windows."
            ],
            "afternoon": [
                "The room holds a comfortable buzz, monitors displaying shifting data under mellow afternoon light.",
                "Wires glint softly while the ozone perfume mingles with the warmth of the fading sun."
            ],
            "late afternoon": [
                "Golden light spills over desks tangled in cables, enhancing the cozy yet industrious atmosphere.",
                "The hum of machines grows steadier, the ozone tang hanging lightly as day turns toward dusk."
            ],
            "night": [
                "Dimmed monitors cast cool blues across the wired desks, the ozone scent deepening in the quiet night.",
                "The room feels both alive and intimate, a world of electronic whispers beneath the cover of darkness."
            ]
        },
        "items": [
                {
                    "name": "usb_drive",
                    "descriptions": [
                        "A small USB drive."
                    ],
                    "static": False,
                    "type": ["tool"]
                },
                {
                    "name": "desktop_computer",
                    "descriptions": [
                        "A desktop computer setup."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "server_rack",
                    "descriptions": [
                        "A rack filled with humming servers."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "network_cable",
                    "descriptions": [
                        "A long ethernet network cable."
                    ],
                    "static": False,
                    "type": ["misc"]
                },
                {
                    "name": "energy_drink",
                    "descriptions": [
                        "A can of sugary, brightly colored energy drink."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 5,
                        "hydration": -10,
                        "energy": 30
                    },
                    "effects": [
                        "You feel a surge of energy!",
                        "A slightly artificial, sweet taste."
                    ]
                },
                {
                    "name": "empty_pizza_box",
                    "descriptions": [
                        "An empty, greasy pizza box."
                    ],
                    "static": False,
                    "type": ["misc"]
                }
            ]
    },
    {
        "name": "garden",
        "image": "garden",
        "room_types": [
            "garden",
            "planting_garden"
        ],
        "plot_number": 6, # if it is a planting garden it needs plot number, it should default to 3?

        "music": "garden",
        "descriptions": {
            "late night": [
                "The garden is enveloped in velvety darkness, with moonlight casting silver shadows on the dense leaves.",
                "A gentle breeze stirs the fragrant blossoms as the nocturnal hum of insects fills the air."
            ],
            "early morning": [
                "Soft dawn light filters through dew-soaked leaves, making the garden glisten with fresh promise.",
                "Birdsong gently awakens the vibrant blooms, and the air smells cool and earthy."
            ],
            "morning": [
                "Sunlight streams warmly into the garden, highlighting bursts of colorful flowers and lush greenery.",
                "The cozy nook invites quiet reflection amid the lively rustle of morning activity."
            ],
            "noon": [
                "Bright midday sun bathes the garden in golden light, intensifying the vivid hues of leaves and petals.",
                "A soothing shade offers respite within the dense foliage, where blooms sway lazily."
            ],
            "afternoon": [
                "The garden thrives under soft, warm light as shadows lengthen and colors deepen.",
                "A comforting hum of bees and the subtle fragrance of blossoms create a serene retreat."
            ],
            "late afternoon": [
                "Golden hour sunlight filters through the leaves, casting dappled patterns across the cozy garden.",
                "The air is rich with floral scents as the greenery glows softly before dusk."
            ],
            "night": [
                "Twinkling stars peek above the silhouette of leaves, while the garden rests in cool, gentle darkness.",
                "Quiet and intimate, the cozy garden feels like a secret haven under the night sky."
            ]
        },
        "items": [
                {
                    "name": "watering_can",
                    "descriptions": [
                        "An old metal watering can, currently full of water."
                    ],
                    "static": False,
                    "type": ["tool"]
                },
                {
                    "name": "garden_shovel",
                    "descriptions": [
                        "A sturdy garden shovel leaning against a tree."
                    ],
                    "static": False,
                    "type": ["tool"]
                },
                {
                    "name": "gardening_gloves",
                    "descriptions": [
                        "A pair of soil-stained gardening gloves."
                    ],
                    "static": False,
                    "type": ["misc"]
                },
                {
                    "name": "bag_of_potting_soil",
                    "descriptions": [
                        "A half-empty bag of rich potting soil."
                    ],
                    "static": False,
                    "type": ["misc"]
                },
                {
                    "name": "ripe_berries",
                    "descriptions": [
                        "A cluster of plump, red berries on a bush."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 8,
                        "hydration": 10,
                        "energy": 4
                    },
                    "effects": [
                        "Sweet and juicy.",
                        "A taste of the garden."
                    ]
                },
                {
                    "name": "fresh_herbs",
                    "descriptions": [
                        "A small bunch of fragrant herbs (looks like mint and basil)."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 2,
                        "hydration": 5,
                        "energy": 5
                    },
                    "effects": [
                        "A strong, aromatic flavor.",
                        "You feel slightly invigorated."
                    ]
                },
                {
                    "name": "small_garden_gnome",
                    "descriptions": [
                        "A ceramic garden gnome with a cheerful expression."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "garden_bench",
                    "descriptions": [
                        "A weathered wooden bench under a tree."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "ice_cold_tea",
                    "descriptions": [
                        "Refreshing ice cold tea"
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 5,
                        "hydration": 30,
                        "energy": 5
                    },
                    "effects": [
                        "A strong, aromatic flavor.",
                        "You feel slightly invigorated."
                    ]
                },
                {'name': 'rose_seeds', 'descriptions': ['Seeds of a beautiful rose plant.', 'Produces fragrant and colorful roses.'], 'static': False, 'type': ['seed'], 'plant_type': 'rose'},
                {'name': 'basil_seeds', 'descriptions': ['Seeds of the aromatic basil herb.', 'Grows fresh basil leaves for cooking.'], 'static': False, 'type': ['seed'], 'plant_type': 'basil'},
                {'name': 'mint_seeds', 'descriptions': ['Seeds of the refreshing mint herb.', 'Grows mint leaves used in teas and recipes.'], 'static': False, 'type': ['seed'], 'plant_type': 'mint'},
                {'name': 'sunflower_seeds', 'descriptions': ['Seeds of a tall sunflower plant.', 'Produces large yellow flowers and edible seeds.'], 'static': False, 'type': ['seed'], 'plant_type': 'sunflower'},
                {'name': 'strawberry_seeds', 'descriptions': ['Seeds of the sweet strawberry plant.', 'Grows delicious red strawberries.'], 'static': False, 'type': ['seed'], 'plant_type': 'strawberry'},
                {'name': 'cactus_seeds', 'descriptions': ['Seeds of the resilient cactus plant.', 'Grows tall and spiky cactus.'], 'static': False, 'type': ['seed'], 'plant_type': 'cactus'}


            ]
    },
    {
        "name": "white_room",
        "image": "white_room",
        "room_types": [
            "white_room"
        ],
        "music": "white_room",
        "descriptions": {
            "late night": [
                "The room pulses with an eerie stillness, its white surfaces glowing faintly under an unseen, ghostly light.",
                "Shadows barely form in the seamless white, the silence thick and unsettling in the deep night."
            ],
            "early morning": [
                "A pale, diffused light creeps invisibly, lending the whiteness a cold, clinical chill.",
                "The room's emptiness feels sharper as faint light hints at the hollow space without revealing its boundaries."
            ],
            "morning": [
                "Soft, neutral light pervades the space, making the seamless whiteness almost blinding in its emptiness.",
                "The stark white room feels vast and hollow, empty but strangely expectant under morning\u2019s glow."
            ],
            "noon": [
                "Bright, unyielding whiteness envelopes the space, erasing any sense of depth or formality.",
                "The room\u2019s seamless whiteness blazes with midday light, sterile and disorienting without any features."
            ],
            "afternoon": [
                "The uniform white continues to dominate, now softer with the slight warmth of afternoon, but no less vacant.",
                "Diffuse light washes the room, the walls seemingly swallowing any sound or movement in the eerie quiet."
            ],
            "late afternoon": [
                "The light fades subtly, casting no shadows yet thickening the room\u2019s oppressive sterility.",
                "A faint yellowish tint seeps into the white, deepening the unsettling emptiness as day wanes."
            ],
            "night": [
                "The white emptiness dims to a spectral pale glow, as if bioluminescent, amplifying the room\u2019s ghostly silence.",
                "Darkness encroaches invisibly, leaving the room an endless void wrapped in an unsettling, muted light."
            ]
        },
        "items": [
                {
                    "name": "stark_white_pedestal",
                    "descriptions": [
                        "A cubic pedestal made of the same seamless white material as the room."
                    ],
                    "static": True,
                    "type": ["furniture"]
                },
                {
                    "name": "faint_symbol",
                    "descriptions": [
                        "A symbol faintly etched into the white surface of the pedestal. It seems to pulse slightly."
                    ],
                    "static": True,
                    "type": ["misc"]
                }
            ]
    },
                {
                    "name": "lab_room",
                    "image": "lab_room",
                    "room_types": ["ALIFE_research"],
                    "music": "white_room",
                    "descriptions": {
    "late night": [
        "A modern laboratory dedicated to A-Life research. The lab is quiet at this late hour.",
        "The light in here is of a deep blue tone, casting long shadows."
    ],
    "early morning": [
        "The lab is just beginning to stir, with a faint hum of machinery.",
        "A cool, crisp light filters through the blinds."
    ],
    "morning": [
        "Activity in the lab is picking up, researchers are at their stations.",
        "Bright, natural light fills the room."
    ],
    "noon": [
        "The lab is bustling with activity.",
        "The overhead lights are at their brightest."
    ],
    "afternoon": [
        "The afternoon slump seems to have hit, some researchers are taking a break.",
        "The blue light feels a bit softer now."
    ],
    "late afternoon": [
        "The lab is starting to wind down, but experiments are still running.",
        "The light outside is beginning to dim, contrasting with the lab's blue glow."
    ],
    "night": [
        "Only a few dedicated researchers remain, the lab is peaceful.",
        "The deep blue light dominates, creating an atmospheric calm."
    ]
},
                    "items": []
                }
],
            "inventory": [],
            # --- Emote State (NEW) ---
            "current_emote": "neutral",
            "possible_emotes": {
                "neutral": "I'm feeling calm and attentive.",
                "happy": "I'm feeling cheerful and optimistic.",
                "sad": "I'm feeling down.",
                "confused": "I'm unsure or puzzled.",
                "excited": "I'm enthusiastic and eager.",
                "thinking": "I'm processing information or contemplating.",
                "angry": "I'm feeling frustrated or upset."
            },
            # --- End Emote State ---

            ## -- health state -- ##
                "stats": {
                "fullness": 200.0,
                "hydration": 200.0,
                "energy": 200.0
            },
    # --- End Stats State -

    # --- NEW: Pet Theme Color Configuration ---
    "is_color_configured": False, # Flag to indicate if the one-time setup is done
    "pet_theme_color": [100, 255, 100], # Default color (green), stored as list for JSON
    "steps": 0
    # --- End Pet Theme Color ---
            # --- End Stats State -
        }
        # --- End of override ---






dev_room={
            # --- Inventory/House State ---
            "next_item_id": ITEM_ID_START_COUNTER,
            "next_room_id": ROOM_ID_START_COUNTER,
            "current_room_id": 0, # Default starting room ID (must match one below)
            "rooms": [
                {
                    "name": "dev_room",
                    "id": 0,
                    "image": "lab_room",
                    "room_types": ["planting_garden"],
                    "plot_number": 3, # if it is a planting garden it needs plot number
                    "music": "white_room",
                    "descriptions": {
    "late night": [
        "A modern computer room, full with servers, cables and screens.",
        "The light in here is of a deep blue tone, casting long shadows."
    ],
    "early morning": [
        "The lab is just beginning to stir, with a faint hum of machinery.",
        "A cool, crisp light filters through the blinds."
    ],
    "morning": [
        "Activity in the lab is picking up, researchers are at their stations.",
        "Bright, natural light fills the room."
    ],
    "noon": [
        "The lab is bustling with activity.",
        "The overhead lights are at their brightest."
    ],
    "afternoon": [
        "The afternoon slump seems to have hit, some researchers are taking a break.",
        "The blue light feels a bit softer now."
    ],
    "late afternoon": [
        "The lab is starting to wind down, but experiments are still running.",
        "The light outside is beginning to dim, contrasting with the lab's blue glow."
    ],
    "night": [
        "Only a few dedicated researchers remain, the lab is peaceful.",
        "The deep blue light dominates, creating an atmospheric calm."
    ]
},
                    "items": []
                }
            ],
            "inventory": [{
        "name": "lettuce seed",
        "descriptions": [
            "A tiny seed, promises a refreshing lettuce."
        ],
        "static": False,
        "type": ["seed"],
        "plant_type": "lettuce" # This key links the seed to its plant type
    }],
            # --- Emote State (NEW) ---
            "current_emote": "neutral",
            "possible_emotes": {
                "neutral": "I'm feeling calm and attentive.",
                "happy": "I'm feeling cheerful and optimistic.",
                "sad": "I'm feeling down.",
                "confused": "I'm unsure or puzzled.",
                "excited": "I'm enthusiastic and eager.",
                "thinking": "I'm processing information or contemplating.",
                "angry": "I'm feeling frustrated or upset."
            },
            # --- End Emote State ---

            ## -- health state -- ##
                "stats": {
                "fullness": 200.0,
                "hydration": 200.0,
                "energy": 200.0
            },
    # --- End Stats State -

    # --- NEW: Pet Theme Color Configuration ---
    "is_color_configured": False, # Flag to indicate if the one-time setup is done
    "pet_theme_color": [100, 255, 100], # Default color (green), stored as list for JSON
    "steps": 0
    # --- End Pet Theme Color ---
            # --- End Stats State -
        }
        # --- End of override ---



how_to_rooms={
            # --- Inventory/House State ---
            "next_item_id": ITEM_ID_START_COUNTER, # Leave this as is
            "next_room_id": ROOM_ID_START_COUNTER, # Leave this as is
            "current_room_id": 0, # You only need to set the ID for the room you want the agent to start the very first time. Set it as 0 for the room you want.
            "rooms": [
                {
                    "name": "dev_room", # A name for the room will be nothing but context
                    "id": 0, # Here we set the ID, and to 0 as we want this to be the very first room on the world.
                    "image": "lab_room", # This is the name of an image inside the folder style/images, add jpg images to this and based on their name change this
                    "room_types": ["dev_room", "bedroom"], # This is tied to the tools the room will have. Tools constructor (tools/tools_builder/construct_tools.py) will use these keys to add the relevant tools to this room. I.E, You could have a room named "Airport" and have it be a kitchen, a lab room and an "airport" type (if any of those tools existed...)
                    "music": "white_room", # Music to be looping while on the room, searches for an mp3 filed named like this inside the folder style/sounds/music/rooms
                    "descriptions": { # Descriptions need to contain all these specific keys for them to be used at different times of the day. Can be manually made or using an AI helper to write them in: data_constructors/room_generator.py 
    "late night": [
        "A modern computer room, full with servers, cables and screens.",
        "The light in here is of a deep blue tone, casting long shadows."
    ],
    "early morning": [
        "The lab is just beginning to stir, with a faint hum of machinery.",
        "A cool, crisp light filters through the blinds."
    ],
    "morning": [
        "Activity in the lab is picking up, researchers are at their stations.",
        "Bright, natural light fills the room."
    ],
    "noon": [
        "The lab is bustling with activity.",
        "The overhead lights are at their brightest."
    ],
    "afternoon": [
        "The afternoon slump seems to have hit, some researchers are taking a break.",
        "The blue light feels a bit softer now."
    ],
    "late afternoon": [
        "The lab is starting to wind down, but experiments are still running.",
        "The light outside is beginning to dim, contrasting with the lab's blue glow."
    ],
    "night": [
        "Only a few dedicated researchers remain, the lab is peaceful.",
        "The deep blue light dominates, creating an atmospheric calm."
    ]
},
                    "items": [      # Here one can populate this with items, Some items need specific data,           
                        {
                    "name": "gardening_gloves", # This is an example of a basic item, all items need at least this information
                    "descriptions": [
                        "A pair of soil-stained gardening gloves."
                    ],
                    "static": False,
                    "type": ["misc"] # This just got updated so items type can be a list of types now, for example, a book seed, if you wanted to do that...
                },                {
                    "name": "mystery_novel", # This is a book item, it needs the base information alongside a chapters structure with any ammount of chapters you like. 
                    "descriptions": [
                        "A paperback novel with a intriguing cover."
                    ],
                    "static": False,
                    "type": ["book"],
                    "chapters": [
                        {
                            "title": "The Gathering Storm",
                            "content": "The rain lashed against the windows as Detective Miles received the anonymous call, the voice on the other end ragged with fear. \"He's gone... they took him,\" the caller choked out before the line went dead, leaving only the sound of distant thunder and Miles's own racing heart. This wasn't the typical petty crime; this felt darker, colder, like the storm brewing outside."
                        },
                        {
                            "title": "A Cryptic Clue",
                            "content": "Beneath the overturned vase, a small, folded piece of paper lay hidden, damp but the ink still legible. It wasn't a name or an address, but a series of symbols and numbers that meant nothing to Miles initially. Yet, there was a deliberate quality to its placement, a message clearly intended to be found, if only by the right eyes."
                        },
                        {
                            "title": "Whispers in the Alley",
                            "content": "Miles followed the breadcrumbs from the cryptic note to a grimy alley behind the old docks, the air thick with the smell of salt and decay. A shadowy figure lingered near overflowing bins, startled by Miles's approach. \"You askin' 'bout the professor?\" the figure rasped, eyes darting nervously. \"Saw him with a couple of rough types, headed towards the abandoned warehouse last night. Looked like they weren't goin' for tea.\"\n\nThe figure, a dockworker named Silas with a reputation for seeing things he shouldn't, reluctantly shared more details. He mentioned a distinctive symbol one of the men wore \u2013 a coiled serpent \u2013 and the specific time they'd passed by. Silas's fear was palpable, whispering that these weren't local thugs, but 'outsiders' who didn't ask questions, they just took what they wanted. His information, though sparse, gave Miles a concrete direction and a chilling confirmation that the professor's disappearance was no accident."
                        },
                        {
                            "title": "The Warehouse's Secret",
                            "content": "The abandoned warehouse loomed by the water, its broken windows like vacant eyes staring out at the choppy sea. Inside, dust motes danced in the few shafts of light filtering through the gaps in the roof. The air was cold, stagnant, and heavy with the scent of mildew and something else... something metallic and faint. Careful footsteps echoed in the vast space as Miles searched, finding scattered crates and forgotten machinery, but no immediate sign of the professor.\n\nHowever, a section of the concrete floor near the back wall seemed newer, less stained than the rest. Prying at a small crack revealed that it wasn't solid concrete, but a cleverly disguised hatch. Beneath it lay not a storage space, but a narrow, descending stairwell leading into absolute darkness, the metallic scent much stronger now. The warehouse wasn't just a drop-off point; it was a gateway to somewhere hidden beneath."
                        }
                    ]
                },
                {
                    "name": "bowl_of_nuts", # This is a consumable item, the extra info it contains is stats_edit and effects
                    "descriptions": [
                        "A small ceramic bowl filled with mixed nuts."
                    ],
                    "static": False,
                    "type": ["consumable"],
                    "stats_edit": {
                        "fullness": 5,
                        "hydration": -2,
                        "energy": 8
                    },
                    "effects": [
                        "A satisfying crunch.",
                        "You feel a slight energy boost."
                    ]
                },
                
                ] # For now, there are no other items that need extra structures, only worry about consumables and books.
                }
            ],
            "inventory": [], # One can populate this with other items if we want to start with them.
            # --- Emote State (NEW) ---
            "current_emote": "neutral", # From the possible emotes, they don't change, each has an animation we need to make if you want to add more
            "possible_emotes": {
                "neutral": "I'm feeling calm and attentive.",
                "happy": "I'm feeling cheerful and optimistic.",
                "sad": "I'm feeling down.",
                "confused": "I'm unsure or puzzled.",
                "excited": "I'm enthusiastic and eager.",
                "thinking": "I'm processing information or contemplating.",
                "angry": "I'm feeling frustrated or upset."
            },
            # --- End Emote State ---

            ## -- health state -- ##
                "stats": { # Consumables and other actions can affect these
                "fullness": 200.0,
                "hydration": 200.0,
                "energy": 200.0
            },
    # --- End Stats State -

    # --- NEW: Pet Theme Color Configuration ---
    "is_color_configured": False, # Flag to indicate if the one-time setup is done, keep as false
    "pet_theme_color": [100, 255, 100], # Default color (green), stored as list for JSON, this color will be overwritten
    "steps": 0 # Starts at 0
    # --- End Pet Theme Color ---
            # --- End Stats State -
        }
        # --- End of override ---

