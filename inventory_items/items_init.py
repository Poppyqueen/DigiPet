
# Define starting IDs for generation.
ITEM_ID_START_COUNTER = 0
ROOM_ID_START_COUNTER = 0

custom_state = {
    # --- Inventory/House State ---
    # These will be updated at the end based on the last ID used
    "next_item_id": ITEM_ID_START_COUNTER, 
    "next_room_id": ROOM_ID_START_COUNTER, 
    "current_room_id": 200005,  # Default starting room ID, we will set up the bedroom as the starting room here
    "rooms": [
        {
            "id": 200001,
            "name": "living_room",
            "descriptions": [
                "A cozy living room, the heart of the house.",
                "A comfortable space with soft lighting and the scent of old books and dust motes dancing in the air."
            ],
            "items": [
                {
                    "id": 0,
                    "name": "sofa",
                    "descriptions": ["A large, plush sofa, perfect for lounging."],
                    "static": True,
                    "type": "furniture"
                },
                {
                    "id": 1,
                    "name": "window",
                    "descriptions": ["A large, window, it has soft white curtains.", "The world outside looks a bit blurry"],
                    "static": True,
                    "type": "furniture"
                },
                {
                    "id": 2,
                    "name": "TV",
                    "descriptions": ["A flat TV, it seems to always be playing something", "It plays whatever it wants"],
                    "static": True,
                    "type": "furniture"
                },
                {
                    "id": 3,
                    "name": "remote_control",
                    "descriptions": ["A universal remote control, slightly sticky."],
                    "static": False,
                    "type": "tool"
                },
                {
                    "id": 4, # Starting new IDs here
                    "name": "coffee_table",
                    "descriptions": ["A sturdy wooden coffee table."],
                    "static": True,
                    "type": "furniture"
                },
                {
                    "id": 5,
                    "name": "bowl_of_nuts",
                    "descriptions": ["A small ceramic bowl filled with mixed nuts."],
                    "static": False,
                    "type": "consumable",
                    "stats_edit": {"fullness": 5, "hydration": -2, "energy": 8},
                    "effects": ["A satisfying crunch.", "You feel a slight energy boost."]
                },
                 {
                    "id": 6,
                    "name": "mystery_novel",
                    "descriptions": ["A paperback novel with a intriguing cover."],
                    "static": False,
                    "type": "book",
                    "chapters": [
                        {"title": "The Gathering Storm", "content": "The rain lashed against the windows as Detective Miles received the anonymous call, the voice on the other end ragged with fear. \"He's gone... they took him,\" the caller choked out before the line went dead, leaving only the sound of distant thunder and Miles's own racing heart. This wasn't the typical petty crime; this felt darker, colder, like the storm brewing outside."},
                        {"title": "A Cryptic Clue", "content": "Beneath the overturned vase, a small, folded piece of paper lay hidden, damp but the ink still legible. It wasn't a name or an address, but a series of symbols and numbers that meant nothing to Miles initially. Yet, there was a deliberate quality to its placement, a message clearly intended to be found, if only by the right eyes."},
                        {"title": "Whispers in the Alley", "content": "Miles followed the breadcrumbs from the cryptic note to a grimy alley behind the old docks, the air thick with the smell of salt and decay. A shadowy figure lingered near overflowing bins, startled by Miles's approach. \"You askin' 'bout the professor?\" the figure rasped, eyes darting nervously. \"Saw him with a couple of rough types, headed towards the abandoned warehouse last night. Looked like they weren't goin' for tea.\"\n\nThe figure, a dockworker named Silas with a reputation for seeing things he shouldn't, reluctantly shared more details. He mentioned a distinctive symbol one of the men wore – a coiled serpent – and the specific time they'd passed by. Silas's fear was palpable, whispering that these weren't local thugs, but 'outsiders' who didn't ask questions, they just took what they wanted. His information, though sparse, gave Miles a concrete direction and a chilling confirmation that the professor's disappearance was no accident."},
                        {"title": "The Warehouse's Secret", "content": "The abandoned warehouse loomed by the water, its broken windows like vacant eyes staring out at the choppy sea. Inside, dust motes danced in the few shafts of light filtering through the gaps in the roof. The air was cold, stagnant, and heavy with the scent of mildew and something else... something metallic and faint. Careful footsteps echoed in the vast space as Miles searched, finding scattered crates and forgotten machinery, but no immediate sign of the professor.\n\nHowever, a section of the concrete floor near the back wall seemed newer, less stained than the rest. Prying at a small crack revealed that it wasn't solid concrete, but a cleverly disguised hatch. Beneath it lay not a storage space, but a narrow, descending stairwell leading into absolute darkness, the metallic scent much stronger now. The warehouse wasn't just a drop-off point; it was a gateway to somewhere hidden beneath."}
                    ]
                },
                 {
                    "id": 7,
                    "name": "woolen_blanket",
                    "descriptions": ["A soft, warm woolen blanket."],
                    "static": False,
                    "type": "misc"
                },
                 {
                    "id": 8,
                    "name": "decorative_vase",
                    "descriptions": ["A tall, ceramic vase with an abstract pattern."],
                    "static": True, # Likely static decor
                    "type": "furniture" 
                },
                 {
                    "id": 9,
                    "name": "old_magazine",
                    "descriptions": ["A slightly outdated magazine with ripped pages."],
                    "static": False,
                    "type": "misc"
                }
            ]
        },
        {
            "id": 200002,
            "name": "kitchen",
            "descriptions": [
                "A modern kitchen, gleaming with stainless steel appliances.",
                "The air smells faintly of spices and cleanliness. Wind streams through the window over the sink."
            ],
            "items": [
                {
                    "id": 10,
                    "name": "apple",
                    "descriptions": ["A fresh, shiny red apple."],
                    "static": False,
                    "type": "consumable",
                    "stats_edit": {"fullness": 10, "hydration": 5, "energy": 5},
                    "effects": ["You feel a little healthier.", "A sweet taste lingers."]
                },
                {
                    "id": 11,
                    "name": "kitchen_knife",
                    "descriptions": ["A sharp chef's knife on a magnetic strip."],
                    "static": False,
                    "type": "tool" # Could be weapon too, but utility is key here
                },
                {
                    "id": 12,
                    "name": "loaf_of_bread",
                    "descriptions": ["A crusty, fresh loaf of bread."],
                    "static": False,
                    "type": "consumable",
                    "stats_edit": {"fullness": 25, "hydration": -5, "energy": 10},
                    "effects": ["Fills you up nicely.", "A satisfyingly simple taste."]
                },
                 {
                    "id": 13,
                    "name": "wedge_of_cheese",
                    "descriptions": ["A tasty-looking wedge of cheddar cheese."],
                    "static": False,
                    "type": "consumable",
                    "stats_edit": {"fullness": 20, "hydration": -1, "energy": 12},
                    "effects": ["Rich and flavorful.", "You feel sustained."]
                },
                 {
                    "id": 14,
                    "name": "can_of_soup",
                    "descriptions": ["A simple can of tomato soup."],
                    "static": False,
                    "type": "consumable", # Assumes it's ready to eat
                    "stats_edit": {"fullness": 20, "hydration": 5, "energy": 15},
                    "effects": ["Warms you up.", "Slightly metallic taste from the can?"]
                },
                 {
                    "id": 15,
                    "name": "bottle_of_water",
                    "descriptions": ["A clear plastic bottle of clean water."],
                    "static": False,
                    "type": "consumable",
                    "stats_edit": {"fullness": 0, "hydration": 40, "energy": 5},
                    "effects": ["Refreshing.", "Quenches your thirst."]
                },
                {
                    "id": 16,
                    "name": "coffee_grounds",
                    "descriptions": ["A bag of aromatic coffee grounds."],
                    "static": False,
                    "type": "consumable", # Could be ingredient for crafting, but let's make it consumable for simplicity
                    "stats_edit": {"fullness": 1, "hydration": -5, "energy": 20}, # Gives energy, dehydrates slightly
                    "effects": ["Very bitter!", "You feel a caffeine kick."]
                },
                 {
                    "id": 17,
                    "name": "spatula",
                    "descriptions": ["A standard rubber spatula."],
                    "static": False,
                    "type": "tool"
                },
                 {
                    "id": 18,
                    "name": "saucepan",
                    "descriptions": ["A medium-sized metal saucepan."],
                    "static": False,
                    "type": "tool"
                },
                 {
                    "id": 19,
                    "name": "cookbook",
                    "descriptions": ["A thick book titled 'Mastering the Culinary Arts'."],
                    "static": False,
                    "type": "book",
                    "chapters": [
                        {"title": "Soups and Stews", "content": "Learn the basics of creating hearty, warming meals that nourish the body and soul. Soups typically involve simmering ingredients in a liquid base, while stews are thicker, featuring larger pieces of meat and vegetables cooked slowly in less liquid. Both techniques are incredibly versatile, allowing you to utilize seasonal ingredients and leftovers efficiently.\n\nMastering a few fundamental stocks – chicken, beef, or vegetable – is key to flavorful soups and stews. Pay attention to simmering times to ensure ingredients are tender but not mushy, and learn how to properly thicken a stew using methods like a roux, reduction, or starches. A well-made soup or stew can be a meal unto itself, perfect for cold evenings."},
                        {"title": "Baking Bread", "content": "From sourdough starters to simple yeast loaves, unlock the secrets of baking your own nourishing bread. The magic lies in understanding the interaction between flour, water, yeast (or wild cultures), and time. Basic yeast bread requires kneading to develop gluten structure, allowing the dough to rise into a light, airy loaf when baked correctly.\n\nExplore different flours – wheat, rye, barley – and experiment with additions like herbs, cheese, or seeds to create a variety of textures and flavors. Perfecting baking temperatures and understanding proofing times are essential steps to achieving that golden crust and soft interior. The smell of fresh-baked bread is one of life's simple, yet profound, pleasures."},
                         {"title": "Desserts", "content": "Indulge your sweet tooth with our collection of cakes, pies, and pastries, ranging from simple fruit tarts to elaborate layered creations. Understanding the role of sugar, fats, and leavening agents is crucial for achieving the desired texture, whether it's a tender crumb, a flaky crust, or a rich custard. Precision in measuring ingredients is often more critical in baking than in savory cooking.\n\nExplore different methods for making pastries, such as the delicate folding required for puff pastry or the simple rubbing-in method for shortcrust. Learn how to create smooth glazes, stable frostings, and vibrant fruit fillings. Baking desserts is a rewarding process that allows for both technical skill and creative expression."},
                         {"title": "Roasting and Braising", "content": "Master the art of transforming cuts of meat and vegetables through controlled heat. Roasting involves cooking with dry heat in an oven or over an open fire, typically at higher temperatures, which is ideal for tender cuts like joints or poultry, creating a delicious browned exterior and succulent interior. Braising, conversely, uses moist heat; the ingredient is often seared first, then cooked slowly in a small amount of liquid in a covered pot, perfect for tougher cuts that become meltingly tender over time.\n\nFor roasting, proper seasoning, basting, and allowing the meat to rest after cooking are key to retaining juices. For braising, selecting the right liquid base (stock, wine, or cider), ensuring the pot is tightly covered to trap steam, and maintaining a low, consistent temperature are paramount. Both techniques can be applied to vegetables as well, yielding intensely flavorful and tender results quite different from other cooking methods."},
                         {"title": "Preserves and Pickles", "content": "Learn how to extend the bounty of the harvest and add vibrant flavors to your larder by preserving fruits and vegetables. Making preserves, like jams, jellies, and chutneys, typically involves cooking fruit with sugar, which acts as a preservative while concentrating flavor and achieving a spreadable consistency. Pickling involves submerging ingredients in an acidic solution, usually vinegar or a salty brine, to inhibit spoilage and impart a tangy flavor.\n\nSuccessfully creating preserves and pickles relies on careful preparation of the ingredients, accurate measurement of sugar or salt/vinegar ratios, and rigorous attention to sterilization to ensure food safety and longevity. Properly sealed jars of homemade preserves and pickles can last for months, providing a taste of peak freshness long after the season has passed and adding bright notes to meals throughout the year."}
                    ]
                }
            ]
        },
        {
            "id": 200003,
            "name": "library",
            "descriptions": [
                "A magnificent library, shelves stretching high towards the ceiling.",
                "The air is thick with the smell of aged paper and leather bindings. A quiet hush permeates the room."
            ],
            "items": [
                {
                    "id": 20,
                    "name": "ancient_tome",
                    "descriptions": ["A dusty, heavy tome bound in weathered leather."],
                    "static": False,
                    "type": "book",
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
                            "content": "Illustrations and descriptions of symbols said to ward off or beckon entities from beyond the veil, these signs are potent conductors of intent and anchors in the non-Euclidean spaces they represent. They are not mere drawings, but diagrams of cosmic forces and pathways, each line and curve imbued with ancient, possibly dangerous, power. Some signs are protective, meant to form barriers against intrusions from the Void, while others are keys, designed to open gates or attract the notice of beings best left undisturbed.\n\nUsing the Elder Signs requires precise execution and a deep understanding of their true meaning, lest one invite disaster instead of protection or communication. Misdrawn or misunderstood, they can backfire horribly, drawing unwelcome attention, causing localized distortions in reality, or even inflicting madness upon the one who invokes them. Caution and reverence are paramount when dealing with these ancient glyphs."
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
                    "id": 21,
                    "name": "comfy_armchair",
                    "descriptions": ["A large, upholstered armchair, perfect for reading."],
                    "static": True,
                    "type": "furniture"
                },
                {
                    "id": 22,
                    "name": "reading_lamp",
                    "descriptions": ["A brass reading lamp next to the armchair."],
                    "static": True, # Integrated into the space
                    "type": "furniture" # Can also be tool, furniture seems more fitting if fixed
                },
                {
                    "id": 23,
                    "name": "journal_with_pen",
                    "descriptions": ["A blank leather-bound journal with a pen tucked into its strap."],
                    "static": False,
                    "type": "book", # Could potentially be used for writing/saving info
                    "chapters": []
                },
                {
                    "id": 24,
                    "name": "history_of_the_realm",
                    "descriptions": ["A comprehensive history book detailing local events."],
                    "static": False,
                    "type": "book",
                    "chapters": [
                        {"title": "The Founding", "content": "The first stones were laid in the year of the Great Stag, when Chieftain Eldrin Ironhand united the scattered tribes of the valley. Facing constant threats from the northern raiders, Eldrin envisioned a fortified settlement, a place where his people could thrive and defend themselves from external aggression. This pivotal moment marked the beginning of recorded history for the realm, establishing the initial boundaries and laying the groundwork for its future development."},
                        {"title": "The Silver War", "content": "A bloody conflict erupted over control of the eastern mines, resources vital to the realm's economy and military strength. Lasting for five brutal years, the war pitted regional lords against the central authority, fueled by greed and ancient rivalries. Villages were razed, trade routes disrupted, and countless lives were lost on both sides of the conflict."},
                         {"title": "Modern Governance", "content": "The current council was established after the treaty of Oakhaven, a fragile peace agreement brokered in the aftermath of the Succession Crisis. This council, composed of representatives from key noble houses and merchant guilds, aims to provide a more stable and equitable form of leadership than the single monarch it replaced. Their decisions guide policy on trade, defense, and justice within the realm's borders."},
                         {"title": "The Great Plague", "content": "In the Year of the Weeping Star, a devastating plague swept across the land, originating in the crowded port cities and quickly spreading inland. The disease claimed nearly a third of the population, leaving villages deserted and throwing the social order into chaos. Healers and alchemists worked tirelessly, but few remedies proved effective against the relentless malady."},
                         {"title": "The Age of Exploration", "content": "Following the plague's retreat, a period of renewed vigor led to the Age of Exploration. Brave captains sailed the uncharted waters of the Sunset Sea, seeking new trade routes and lands. These voyages brought back exotic goods, strange knowledge, and sometimes, new conflicts with the peoples encountered beyond the known world. Mapmakers became invaluable as the realm's understanding of the globe expanded significantly."},
                         {"title": "The Ironwood Treaties", "content": "Centuries after the founding, a series of treaties known as the Ironwood Treaties solidified the realm's borders and established long-lasting alliances with neighboring kingdoms. These agreements, hammered out over decades of negotiation and minor skirmishes, defined spheres of influence and mutual defense pacts. While not entirely eliminating border disputes, they ushered in an era of relative peace and increased diplomatic ties."}
                    ]
                },
                 {
                    "id": 25,
                    "name": "atlas_of_the_world",
                    "descriptions": ["A large, detailed atlas with maps of various regions."],
                    "static": False,
                    "type": "book", # Treat maps as read-only info
                    "chapters": [
                        {"title": "The Western Continents", "content": "Explore the vast lands beyond the Sunset Sea... (Detailed map follows)\n\nThese continents are home to diverse empires, soaring mountain ranges, and deep, ancient forests. From the temperate northern coasts to the sun-scorched southern plains, life thrives in countless forms and civilizations rise and fall like the tides. Studying the terrain and key locations on the map is vital for understanding the history and power dynamics of this dominant landmass."},
                        {"title": "The Eastern Isles", "content": "A chain of volcanic islands known for their unique flora and fauna... (Detailed map follows)\n\nStretching across the Eastern Ocean, these islands range from steaming volcanic peaks to lush, secluded lagoons. Many species here are found nowhere else in the world, adapted to the islands' isolated ecosystems and frequent seismic activity. Navigating the treacherous currents between islands and identifying safe harbors requires careful consultation of the included maritime charts."},
                        {"title": "The Northern Reaches", "content": "Journey into the lands of ice and frost... (Detailed map follows)\n\nFar beyond the temperate zones lies the unforgiving expanse of the Northern Reaches. This territory is dominated by immense glaciers, frozen tundras, and jagged fjords that carve into a desolate coastline. Survival here is a constant battle against the elements, with long, dark winters and biting winds sweeping across the frozen plains."},
                        {"title": "The Shifting Sands", "content": "Uncover the secrets buried beneath the dunes... (Detailed map follows)\n\nTo the south, stretching further than the eye can see, is the vast and deadly territory known as the Shifting Sands. This immense desert is a sea of dunes, where landmarks are few and water is a precious rarity. Ancient ruins are said to lie half-buried beneath the sand, remnants of civilizations claimed by the scorching heat and endless drought."},
                        {"title": "The Underworld Depths", "content": "Descend into the caverns below... (Detailed map follows)\n\nNot all lands exist under the sun; beneath the surface lies a complex network of caverns, tunnels, and vast subterranean lakes known collectively as the Underworld Depths. Home to unique geological formations and species adapted to eternal darkness, this region presents an entirely different challenge for explorers. The map details known primary routes and major chambers, though countless unexplored passages remain hidden."},
                        {"title": "The Sky Islands", "content": "Ascend to the floating landmasses... (Detailed map follows)\n\nA truly unique phenomenon are the Sky Islands, great chunks of land that mysteriously float high above the surface world. These islands possess their own peculiar climates and ecosystems, some supporting strange flora and fauna, others containing rare minerals drawn upwards from deep within the earth. The map indicates approximate positions and known stable platforms, though movement and altitude can vary."}
                    ]
                },
                 {
                    "id": 26,
                    "name": "poetry_anthology",
                    "descriptions": ["A collection of modern and contemporary poems."],
                    "static": False,
                    "type": "book",
                    "chapters": [
                        {"title": "City Scratches", "content": "Cobblestones gleam, slick with rain,\ncarrying the tired lamplight down drain.\nGhost of footsteps echo in the narrow space,\na forgotten scent, a hurried pace.\n\nHigh window, a single yellow square,\nholds somebody breathing the damp air.\nThe city breathes, a low, wet sigh,\nbeneath a sky the color of a bruised eye."},
                        {"title": "Root-Bound Silence", "content": "Beneath the ancient oak's spread,\nwhere tangled roots make a tangled bed,\nthe air hangs thick, tasting of earth and mold,\nsecrets the silent stones have held.\n\nA single dewdrop clings to a spider's thread,\nreflecting a sunbeam, barely shed.\nNo birdsong here, no rustling leaf,\njust the deep, slow breath of green relief."},
                        {"title": "The Hum Behind the Eyes", "content": "The world outside is sharp, defined,\nbut inside the hum is hard to find.\nA low vibration, behind the bone,\na radio frequency, tuned to the unknown.\n\nSometimes it whispers, sometimes it screams,\na static haze over waking dreams.\nIs it my own pulse, or something vast,\na message from a future or the past?"}
                    ]
                },
                 {
                    "id": 27,
                    "name": "botany_guide",
                    "descriptions": ["A guide to identifying local plants and their uses."],
                    "static": False,
                    "type": "book",
                     "chapters": [
                        {"title": "Identifying Common Herbs", "content": "Learn to distinguish between Feverfew, Comfrey, and Valerian, three of the most frequently encountered and utilized herbs in the realm. Feverfew is recognized by its small, daisy-like flowers and pungent scent, commonly used for headaches and fevers. Comfrey, with its large, hairy leaves and bell-shaped flowers, is renowned for its ability to aid bone and tissue healing, though internal use is cautioned against.\n\nValerian is identified by its strong, distinct odor and clusters of small pink or white flowers atop a tall stem; it is a potent relaxant and sleep aid. Mastering the identification of these foundational herbs is crucial for any aspiring healer or traveler needing basic medicinal knowledge in the wild."},
                        {"title": "Edible Wild Plants", "content": "A guide to foraging safely for berries, roots, and leaves that can provide sustenance when other food sources are scarce. Important examples include the Sweetroot, a tuber found in moist soil identifiable by its broad leaves, which is nutritious when roasted. Wild Greens, such as those resembling nettles but lacking their sting, can be boiled to remove bitterness and provide essential vitamins.\n\nAlways positively identify a plant multiple times before consuming it, as many edible species have poisonous look-alikes. Pay attention to leaf shape, stem structure, growth location, and any flowers or fruits. When in doubt, do not eat it; even small amounts of certain plants can be deadly."},
                        {"title": "Poisonous Species", "content": "Crucial information on plants to avoid at all costs, as ingestion or even contact can cause severe harm or death. The Deathcap Mushroom, while not a plant, is often mistaken for edible fungi and is lethally toxic, identifiable by its white gills, ring on the stem, and volva cup at the base. The Hemlock plant, with its purple-spotted stem and parsley-like leaves, is another highly poisonous species; even a small amount ingested can cause respiratory failure.\n\nLearn the appearance of common irritants like Itchvine, which causes blistering rashes upon contact, and airborne irritants from certain flowering plants that can cause severe allergic reactions. Carrying a small amount of purifying poultice or antidote is advised when traveling through areas known for dangerous flora, and always treat unknown plants with extreme caution."},
                        {"title": "Trees of the Whispering Woods", "content": "The Whispering Woods are dominated by several key tree species, each with distinct characteristics. The Ironwood, named for the incredible density and strength of its timber, is easily recognized by its deeply furrowed, dark bark and broad, persistent leaves. The Moonpetal Birch, on the other hand, has smooth, silver-white bark that peels like paper, and delicate, pale leaves that seem to glow faintly in twilight.\n\nIdentifying these trees is vital for woodcutters and builders; Ironwood is prized for fortifications and weapons, while Moonpetal Birch wood is lighter, easier to work, and often used in fine furniture or carvings. Pay attention to bark texture, leaf shape, and the arrangement of branches, as these are the primary identifiers when the trees are bare in winter."},
                        {"title": "Fungi of the Damp Caves", "content": "The subterranean environments of the Damp Caves host a unique ecosystem dominated by various fungal lifeforms adapted to perpetual darkness. The Glowcap, a bioluminescent mushroom, provides the primary light source in many caverns and is identifiable by its soft blue or green light emanating from the cap's underside. The Stonefoot Fungus, found growing directly on damp rock faces, is tough and rubbery, often serving as a minor food source for cavern dwellers.\n\nWhile many cave fungi are harmless or have specific, often minor, effects, some can be toxic or even explosive if disturbed. Always observe subterranean fungi from a distance before interacting, noting their color, growth pattern, and any unusual emanations or scents. The Glowcap's light is useful for navigation, but caution is advised with less well-documented species."},
                        {"title": "Desert Cacti and Succulents", "content": "Surviving in the harsh environment of the Shifting Sands requires understanding the flora adapted to extreme drought and heat. Barrel Cacti are common, identifiable by their ribbed, cylindrical shape and formidable spines; their inner pulp can provide a small amount of emergency water when carefully extracted. The Dune Lily, a succulent with thick, fleshy leaves often buried except for the tips, stores water and nutrients underground.\n\nMany desert plants are spiny or possess irritants as defense mechanisms against dehydration and predation. Learn to distinguish edible or useful species from purely defensive ones. The presence of certain succulents can also indicate slightly higher water tables, making them valuable markers for travelers seeking oases or subterranean water sources."}
                    ]
                }
            ]
        },
        {
            "id": 200004,
            "name": "bathroom",
            "descriptions": [
                "A clean, tiled bathroom with a large mirror.",
                "The air is slightly humid, smelling faintly of floral soap and toothpaste."
            ],
            "items": [
                {
                    "id": 28,
                    "name": "soap_bar",
                    "descriptions": ["A bar of fragrant lavender soap."],
                    "static": False,
                    "type": "consumable", # Let's adjust stats, less hydration, maybe some energy/cleanliness effect
                    "stats_edit": {"fullness": 0, "hydration": 5, "energy": 2},
                    "effects": ["You feel fresh and clean.", "The smell is quite pleasant."]
                },
                 {
                    "id": 29,
                    "name": "toothbrush",
                    "descriptions": ["A simple plastic toothbrush."],
                    "static": False,
                    "type": "tool"
                },
                 {
                    "id": 30,
                    "name": "tube_of_toothpaste",
                    "descriptions": ["A tube of mint-flavored toothpaste."],
                    "static": False,
                    "type": "consumable",
                    "stats_edit": {"fullness": 0, "hydration": 8, "energy": 3}, # Small hydration/energy boost for freshness
                    "effects": ["Your mouth feels clean and minty.", "A slight tingle."]
                },
                {
                    "id": 31,
                    "name": "clean_towel",
                    "descriptions": ["A fluffy white towel hanging on a rack."],
                    "static": False,
                    "type": "misc"
                },
                {
                    "id": 32,
                    "name": "medicine_cabinet",
                    "descriptions": ["A metal medicine cabinet mounted on the wall."],
                    "static": True,
                    "type": "furniture"
                },
                {
                    "id": 33,
                    "name": "pain_relievers",
                    "descriptions": ["A bottle of common pain relievers."],
                    "static": False,
                    "type": "consumable",
                    "stats_edit": {"fullness": 0, "hydration": 5, "energy": 20}, # Can give a small boost
                    "effects": ["You feel a dull ache subside.", "A slightly chalky taste."]
                }
            ]
        },
        {
            "id": 200005,
            "name": "bedroom",
            "descriptions": [
                "A peaceful bedroom, dominated by a large, inviting bed.",
                "Soft wind sways the curtains, there is low light."
            ],
            "items": [
                {
                    "id": 34,
                    "name": "pillow",
                    "descriptions": ["A soft, fluffy pillow on the bed."],
                    "static": True, # Part of the bed furniture essentially
                    "type": "furniture"
                },
                {
                    "id": 35,
                    "name": "bedside_novel",
                    "descriptions": ["A well-worn novel left open on the nightstand."],
                    "static": False,
                    "type": "book",
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
                            "content": "The path forward was no longer a simple journey towards a vague destination, but a focused quest with a specific, urgent goal dictated by a being beyond comprehension. The symbol burned faintly in the protagonist's thoughts, a constant reminder of the task. Consulting worn maps and piecing together fragmented legends, it became clear that the object mentioned by the Whisperer was tied to a region far from the original route, a place whispered about only in hushed tones by fearful villagers.\n\nThis new destination lay through territory rumored to be cursed, haunted by lingering energies from ancient conflicts. The cheerful optimism that had fueled the initial journey was replaced by a grim determination. The stakes had been raised immeasurably, and the traveler understood that failure was not merely a personal setback, but potentially a cosmic catastrophe. The journey had truly just begun, leading now into the heart of true peril."
                        }
                    ]
                },
                 {
                    "id": 36,
                    "name": "large_bed",
                    "descriptions": ["A large, comfortable bed with clean sheets."],
                    "static": True,
                    "type": "furniture"
                },
                {
                    "id": 37,
                    "name": "wardrobe",
                    "descriptions": ["A wooden wardrobe filled with clothes."],
                    "static": True,
                    "type": "furniture"
                },
                {
                    "id": 38,
                    "name": "cozy_sweater",
                    "descriptions": ["A thick, knitted sweater."],
                    "static": False,
                    "type": "armor", # Or misc, but armor suggests wearing for warmth/minor protection
                     "stats_edit": {"energy": 5}, # Might give a slight energy boost from feeling warm/comfortable
                     "effects": ["You feel warm and snug.", "Blocks a small amount of chill."]
                },
                 {
                    "id": 39,
                    "name": "alarm_clock",
                    "descriptions": ["A digital alarm clock on the nightstand."],
                    "static": True, # Usually static furniture
                    "type": "furniture" # Or tool if it has interactive functions
                },
                {
                    "id": 40,
                    "name": "personal_diary",
                    "descriptions": ["A locked diary with a small heart-shaped clasp."],
                    "static": False,
                    "type": "book", # Could be a book if unlocked
                    "chapters": []
                },
                 {
                    "id": 41,
                    "name": "glass_of_water",
                    "descriptions": ["A glass of water on the nightstand."],
                    "static": False,
                    "type": "consumable",
                    "stats_edit": {"fullness": 2, "hydration": 25, "energy": 3},
                    "effects": ["Refeshing.", "Cool and pure."]
                }
            ]
        },
        {
            "id": 200006,
            "name": "computer_room",
            "descriptions": [
                "A room filled with the quiet hum of electronic machines.",
                "Desks are covered in wires and monitors. The air smells faintly of ozone."
            ],
            "items": [
                {
                    "id": 42,
                    "name": "usb_drive",
                    "descriptions": ["A small USB drive."],
                    "static": False,
                    "type": "tool" # Or misc, but 'tool' implies function
                },
                {
                    "id": 43,
                    "name": "desktop_computer",
                    "descriptions": ["A desktop computer setup."],
                    "static": True,
                    "type": "furniture" # Or tool/furniture combined
                },
                {
                    "id": 44,
                    "name": "server_rack",
                    "descriptions": ["A rack filled with humming servers."],
                    "static": True,
                    "type": "furniture" # Or tool/furniture combined
                },
                 {
                    "id": 45,
                    "name": "network_cable",
                    "descriptions": ["A long ethernet network cable."],
                    "static": False,
                    "type": "misc" # Tool or misc depending on interaction
                },
                {
                    "id": 46,
                    "name": "energy_drink",
                    "descriptions": ["A can of sugary, brightly colored energy drink."],
                    "static": False,
                    "type": "consumable",
                    "stats_edit": {"fullness": 5, "hydration": -10, "energy": 30}, # Big energy boost, dehydrates
                    "effects": ["You feel a surge of energy!", "A slightly artificial, sweet taste."]
                },
                 {
                    "id": 47,
                    "name": "empty_pizza_box",
                    "descriptions": ["An empty, greasy pizza box."],
                    "static": False,
                    "type": "misc" # Used consumable or just trash
                }
            ]
        },
        {
            "id": 200007,
            "name": "garden",
            "descriptions": [
                "A lush garden, bursting with greenery and color.",
                "Bees hum among the flowers. The air is fresh and earthy."
            ],
            "items": [
                {
                    "id": 48,
                    "name": "watering_can",
                    "descriptions": ["An old metal watering can, currently full of water."],
                    "static": False,
                    "type": "tool"
                },
                {
                    "id": 49,
                    "name": "garden_shovel",
                    "descriptions": ["A sturdy garden shovel leaning against a tree."],
                    "static": False,
                    "type": "tool"
                },
                 {
                    "id": 50,
                    "name": "gardening_gloves",
                    "descriptions": ["A pair of soil-stained gardening gloves."],
                    "static": False,
                    "type": "misc" # Or tool if they enable specific actions
                },
                 {
                    "id": 51,
                    "name": "bag_of_potting_soil",
                    "descriptions": ["A half-empty bag of rich potting soil."],
                    "static": False,
                    "type": "misc"
                },
                 {
                    "id": 52,
                    "name": "ripe_berries",
                    "descriptions": ["A cluster of plump, red berries on a bush."],
                    "static": False, # Can be picked
                    "type": "consumable",
                    "stats_edit": {"fullness": 8, "hydration": 10, "energy": 4},
                    "effects": ["Sweet and juicy.", "A taste of the garden."]
                },
                 {
                    "id": 53,
                    "name": "fresh_herbs",
                    "descriptions": ["A small bunch of fragrant herbs (looks like mint and basil)."],
                    "static": False, # Can be picked
                    "type": "consumable", # Can be consumed directly or used for crafting
                    "stats_edit": {"fullness": 2, "hydration": 5, "energy": 5},
                    "effects": ["A strong, aromatic flavor.", "You feel slightly invigorated."]
                },
                 {
                    "id": 54,
                    "name": "small_garden_gnome",
                    "descriptions": ["A ceramic garden gnome with a cheerful expression."],
                    "static": True, # Static decor
                    "type": "furniture" # Or misc
                },
                {
                    "id": 55,
                    "name": "garden_bench",
                    "descriptions": ["A weathered wooden bench under a tree."],
                    "static": True,
                    "type": "furniture"
                },                 
                {
                    "id": 56,
                    "name": "ice_cold_tea",
                    "descriptions": ["Refreshing ice cold tea"],
                    "static": False, # Can be picked
                    "type": "consumable", # Can be consumed directly or used for crafting
                    "stats_edit": {"fullness": 5, "hydration": 30, "energy": 5},
                    "effects": ["A strong, aromatic flavor.", "You feel slightly invigorated."]
                },
            ]
        },
        {
            "id": 200008,
            "name": "white_room",
            "descriptions": [
                "An unsettlingly empty white room.",
                "The walls, floor, and ceiling are seamless and pure white. There are no windows or doors visible initially, just a uniform, featureless space." # Added more detail
            ],
            "items": [
                # Let's make it intriguing
                {
                    "id": 57,
                    "name": "stark_white_pedestal",
                    "descriptions": ["A cubic pedestal made of the same seamless white material as the room."],
                    "static": True,
                    "type": "furniture"
                },
                 {
                    "id": 58,
                    "name": "faint_symbol",
                    "descriptions": ["A symbol faintly etched into the white surface of the pedestal. It seems to pulse slightly."],
                    "static": True, # Part of the static furniture/room
                    "type": "misc" # Not really an item to pick up, but something to observe/interact with
                }
            ]
        }
    ],
    "inventory": [], # Inventory starts empty
    # --- Emote State ---
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

    # --- Stats State ---
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
    # --- End Stats State ---
}



base_state={
            # --- Inventory/House State ---
            "next_item_id": ITEM_ID_START_COUNTER,
            "next_room_id": ROOM_ID_START_COUNTER,
            "current_room_id": 200001, # Default starting room ID (must match one below)
            "rooms": [
                {
                    "id": 200001,
                    "name": "living_room",
                    "descriptions": [
                        "A comfortable living room with a fireplace.",
                        "Sunlight streams through the large window."
                    ],
                    "items": [
                        {
                            "id": 100001,
                            "name": "sofa",
                            "descriptions": ["A large, comfy sofa.", "It looks well-worn."],
                            "static": True,
                            "type": "furniture"
                        },
                         {
                            "id": 100002,
                            "name": "remote_control",
                            "descriptions": ["A universal remote control.", "It has many buttons."],
                            "static": False,
                            "type": "tool"
                        },
                         {
                            "id": 100099,
                            "name": "pizza_slice",
                            "descriptions": ["A cold pepperoni pizza slice", "It got here yesterday"],
                            "static": False,
                            "type": "consumable",
                            "stats_edit": {"fullness":20,
                                        "hydration": -10,
                                        "energy": 10},
                            "effects": ["Even tho it is cold, it is tasty", "The spices it has make you feel a bit energized, and thirsty"]
                        }
                    ]
                },
                {
                    "id": 200002,
                    "name": "kitchen",
                    "descriptions": [
                        "A clean, modern kitchen.",
                        "The smell of fresh coffee lingers."
                    ],
                    "items": []
                },
                {
                    "id": 200003,
                    "name": "library",
                    "descriptions": [
                        "A clean, modern library.",
                        "It looks quite dark"
                    ],
                    "items": []
                }
            ],
            "inventory": [
                {
                    "id": 100003,
                    "name": "old_key",
                    "descriptions": ["A small, rusty key.", "It might open something."],
                    "static": False,
                    "type": "key"
                },
                 # Default Book Item with ID and Chapters
                 {
                     "id": 100004,
                     "name": "Mysteries of the Cozy House",
                     "descriptions": ["A worn leather-bound book.", "Seems to be a personal journal."],
                     "static": False,
                     "type": "book",
                     "chapters": [
                         {
                             "title": "The Creaking Floorboard",
                             "content": "It was a dark and stormy night..."
                         },
                         {
                             "title": "Whispers in the Walls",
                             "content": "They say the house has secrets..."
                         }
                     ]
                 }
            ],
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