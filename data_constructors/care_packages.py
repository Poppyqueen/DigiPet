care_package_1_general_survival = [
    {
        "name": "water_bottle",
        "descriptions": ["A standard plastic water bottle", "Sealed and clean", "Essential hydration"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 30,
            "energy": 0
        },
        "effects": ["Quenches your thirst effectively", "Leaves you feeling refreshed"]
    },
    {
        "name": "energy_bar",
        "descriptions": ["A high-energy snack bar", "Compact and portable", "Sweet and chewy"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": -5,
            "energy": 25
        },
        "effects": ["You feel a quick surge of energy", "It leaves a slight dryness in your mouth"]
    },
    {
        "name": "canned_beans",
        "descriptions": ["A can of hearty baked beans", "Provides sustained energy", "Best when heated"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 30,
            "hydration": 10,
            "energy": 15
        },
        "effects": ["Fills your stomach well", "Provides good, slow-release energy"]
    },
    {
        "name": "crackers_pack",
        "descriptions": ["A small pack of plain crackers", "Dry but filling", "Goes well with other foods"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 15,
            "hydration": -10,
            "energy": 5
        },
        "effects": ["Slightly dry on the palate", "Provides a basic crunchy snack"]
    },
    {
        "name": "apple",
        "descriptions": ["A fresh, crisp apple", "Natural energy source", "Good for a quick bite"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": 5,
            "energy": 10
        },
        "effects": ["Refreshing and slightly sweet", "Gives you a small burst of energy"]
    },
    {
        "name": "trail_mix",
        "descriptions": ["A bag of nuts, seeds, and dried fruit", "High in calories and nutrients", "Great for sustained effort"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 20,
            "hydration": -5,
            "energy": 20
        },
        "effects": ["A good mix of textures and flavors", "Provides lasting energy"]
    },
     {
        "name": "chocolate_bar",
        "descriptions": ["A standard milk chocolate bar", "Quick sugar boost", "Comforting treat"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": -5,
            "energy": 15
        },
        "effects": ["A sweet, temporary uplift", "Quickly melts away"]
    },
     {
        "name": "water_bottle", # Repeat item for extra hydration
        "descriptions": ["Another standard plastic water bottle", "Sealed and clean", "More essential hydration"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 30,
            "energy": 0
        },
        "effects": ["More thirst quenched", "Feeling even more hydrated"]
    }
]

care_package_2_hydration_refreshment = [
    {
        "name": "water_bottle",
        "descriptions": ["A standard plastic water bottle", "Sealed and clean", "Essential hydration"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 30,
            "energy": 0
        },
        "effects": ["Quenches your thirst effectively", "Leaves you feeling refreshed"]
    },
     {
        "name": "water_bottle", # Repeat
        "descriptions": ["Another standard plastic water bottle", "Sealed and clean", "More essential hydration"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 30,
            "energy": 0
        },
        "effects": ["More thirst quenched", "Feeling even more hydrated"]
    },
    {
        "name": "juice_box",
        "descriptions": ["A small carton of fruit juice", "Sweet and hydrating", "Easy to drink on the go"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 20,
            "energy": 20
        },
        "effects": ["A sweet, fruity burst", "Helps rehydrate with some sugar"]
    },
    {
        "name": "orange",
        "descriptions": ["A juicy, fresh orange", "High in vitamin C", "Segmented and easy to eat"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": 15,
            "energy": 8
        },
        "effects": ["Sweet, tangy, and very juicy", "Provides a natural hydration boost"]
    },
    {
        "name": "fruit_salad_cup",
        "descriptions": ["A cup of mixed fruit pieces", "Sweet and refreshing", "Contains berries, melon, and grapes"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 15,
            "hydration": 25,
            "energy": 12
        },
        "effects": ["A delightful mix of flavors and textures", "Excellent for cooling down and hydrating"]
    },
    {
        "name": "soda_can",
        "descriptions": ["A can of fizzy sugary drink", "Not the best for hydration, but quick energy", "Cold and bubbly"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": -10, # Can sometimes dehydrate slightly due to sugar/caffeine
            "energy": 15
        },
        "effects": ["A sudden sugar rush", "Leaves you slightly more thirsty than before"]
    },
    {
        "name": "flavored_drink_mix",
        "descriptions": ["A small sachet of powdered drink mix", "Add to water for flavor", "Makes plain water more appealing"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 0,
            "hydration": 5, # Slight boost to hydration feel
            "energy": 3 # Small sugar/flavor boost
        },
        "effects": ["Transforms plain water into a tasty drink", "Makes staying hydrated feel easier"]
    },
     {
        "name": "juice_box", # Repeat
        "descriptions": ["Another small carton of fruit juice", "Sweet and hydrating", "More easy liquid energy"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 20,
            "energy": 30
        },
        "effects": ["Another sweet, fruity burst", "Keeps the hydration coming and sugar pumping"]
    }
]

care_package_3_hearty_meal_kit = [
    {
        "name": "canned_stew",
        "descriptions": ["A can of thick, hearty meat stew", "A proper meal in a can", "Needs warming for best results"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 40,
            "hydration": 10,
            "energy": 20
        },
        "effects": ["Feels like a substantial meal", "Leaves you feeling warm and satisfied"]
    },
    {
        "name": "canned_tuna",
        "descriptions": ["A can of tuna in oil or water", "Good source of protein", "Simple and versatile"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 25,
            "hydration": 5,
            "energy": 10
        },
        "effects": ["Provides solid protein", "A bit plain on its own"]
    },
    {
        "name": "mre_main_course",
        "descriptions": ["The main dish component of a Meal, Ready-to-Eat", "Sealed and durable packaging", "A complete, if unexciting, meal"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 50,
            "hydration": 10,
            "energy": 30
        },
        "effects": ["Definitely fills you up", "Provides all-around sustenance"]
    },
    {
        "name": "hard_biscuits",
        "descriptions": ["A packet of dense, hard biscuits", "Ideal for dipping in soup or stew", "Very durable"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 20,
            "hydration": -15,
            "energy": 8
        },
        "effects": ["Requires some effort to chew", "Very dry, but provides good carbs"]
    },
    {
        "name": "pudding_cup",
        "descriptions": ["A small cup of ready-to-eat pudding", "A simple, sweet dessert", "Provides a morale boost"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 5,
            "energy": 7
        },
        "effects": ["A nice, sweet finish to a meal", "Adds a little comfort"]
    },
    {
        "name": "water_bottle", # Still need water!
        "descriptions": ["A standard plastic water bottle", "Sealed and clean", "Essential hydration"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 30,
            "energy": 0
        },
        "effects": ["Quenches your thirst effectively", "Leaves you feeling refreshed"]
    },
    {
        "name": "dried_apricots",
        "descriptions": ["A bag of chewy dried apricots", "Sweet and slightly tangy", "Good source of fiber and sugar"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": -5,
            "energy": 10
        },
        "effects": ["Chewy and sweet", "Gives a quick sugar boost"]
    },
    {
        "name": "canned_chicken",
        "descriptions": ["A can of cooked chicken pieces", "Lean protein source", "Good for adding to other dishes or eating plain"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 25,
            "hydration": 5,
            "energy": 12
        },
        "effects": ["Provides filling protein", "Can be a bit bland on its own"]
    }
]

care_package_4_quick_snacks_energy = [
    {
        "name": "energy_bar", # Multiple energy bars
        "descriptions": ["A high-energy snack bar", "Compact and portable", "Sweet and chewy"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": -5,
            "energy": 25
        },
        "effects": ["You feel a quick surge of energy", "It leaves a slight dryness in your mouth"]
    },
    {
        "name": "energy_bar", # Repeat
        "descriptions": ["Another high-energy snack bar", "Quick and convenient energy", "Good for on the move"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": -5,
            "energy": 25
        },
        "effects": ["Another quick energy boost", "Perfect for a rapid refuel"]
    },
    {
        "name": "chocolate_bar", # Multiple chocolate bars
        "descriptions": ["A standard milk chocolate bar", "Quick sugar boost", "Comforting treat"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": -5,
            "energy": 15
        },
        "effects": ["A sweet, temporary uplift", "Quickly melts away"]
    },
    {
        "name": "potato_chips_bag",
        "descriptions": ["A small bag of crunchy potato chips", "Salty snack", "Satisfies cravings"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": -10,
            "energy": 8
        },
        "effects": ["Pleasingly crunchy and salty", "Definitely makes you want a drink"]
    },
    {
        "name": "beef_jerky",
        "descriptions": ["A strip of dried and seasoned beef", "High protein snack", "Requires some chewing"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 15,
            "hydration": -15,
            "energy": 10
        },
        "effects": ["Provides sustained protein", "Very chewy and dry"]
    },
    {
        "name": "trail_mix",
        "descriptions": ["A bag of nuts, seeds, and dried fruit", "High in calories and nutrients", "Great for sustained effort"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 20,
            "hydration": -5,
            "energy": 20
        },
        "effects": ["A good mix of textures and flavors", "Provides lasting energy"]
    },
    {
        "name": "soda_can", # Quick liquid energy
        "descriptions": ["A can of fizzy sugary drink", "Not the best for hydration, but quick energy", "Cold and bubbly"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": -10, # Can sometimes dehydrate slightly due to sugar/caffeine
            "energy": 15
        },
        "effects": ["A sudden sugar rush", "Leaves you slightly more thirsty than before"]
    },
     {
        "name": "small_nut_bag",
        "descriptions": ["A small bag of mixed nuts", "Good source of fat and protein", "Crunchy snack"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": -5,
            "energy": 10
        },
        "effects": ["Provides a satisfying crunch", "A good source of healthy fats"]
    },
    {
        "name": "sweet_crackers",
        "descriptions": ["A small pack of sweet, slightly crumbly crackers", "A simple sugary snack", "Better than nothing for a sweet tooth"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 8,
            "hydration": -5,
            "energy": 8
        },
        "effects": ["A simple, sweet bite", "Leaves a few crumbs"]
    }
]


care_package_friend_comfort_food = [
    {
        "name": "pizza_slice_cold",
        "descriptions": ["A leftover slice of delicious pizza", "Surprisingly good cold", "Extra cheesy"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 25,
            "hydration": -15,
            "energy": 15
        },
        "effects": ["Pure comfort in a slice", "Leaves a bit of grease on your fingers and makes you thirsty"]
    },
    {
        "name": "cola_can",
        "descriptions": ["A chilled can of fizzy cola", "Sweet and bubbly", "The classic sugary drink"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 3,
            "hydration": -10, # Sodas often dehydrate more than they hydrate due to sugar/caffeine
            "energy": 20
        },
        "effects": ["A satisfying sugary rush", "Makes your mouth feel a little sticky and dry afterwards"]
    },
    {
        "name": "potato_chips_large_bag",
        "descriptions": ["A big bag of your favorite crispy potato chips", "Salty and crunchy", "Warning: Highly addictive"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 15,
            "hydration": -20,
            "energy": 10
        },
        "effects": ["The perfect salty crunch", "You'll immediately need a drink after eating these"]
    },
    {
        "name": "chocolate_bar_king_size",
        "descriptions": ["A large, extra-indulgent chocolate bar", "Rich and sweet", "Melts in your mouth"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 8,
            "hydration": -8,
            "energy": 25
        },
        "effects": ["Decadent sweetness washes over you", "Provides a strong, but possibly short-lived, energy boost"]
    },
    {
        "name": "cheese_puffs_bag",
        "descriptions": ["A bag of brightly colored, cheesy puffs", "Light and airy, but packed with flavor", "Leaves cheesy dust everywhere"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": -15,
            "energy": 8
        },
        "effects": ["Incredibly cheesy and satisfying", "Your fingers are now covered in cheese powder"]
    },
    {
        "name": "packaged_donut",
        "descriptions": ["A individually packaged glazed donut", "Soft, sweet, and convenient", "A simple sugary pleasure"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": -5,
            "energy": 12
        },
        "effects": ["Sweet, simple comfort", "Goes down easy, maybe too easy"]
    },
    {
        "name": "cookies_packet_chocolate_chip",
        "descriptions": ["A small packet of classic chocolate chip cookies", "Crunchy edges, soft center (hopefully!)", "Just like home"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": -10,
            "energy": 10
        },
        "effects": ["Sweet and familiar", "Best dunked in milk (if you had any!)"]
    },
    {
        "name": "candy_assortment_bag",
        "descriptions": ["A mix of various sugary candies", "Fruity, chewy, hard candies", "A little bit of everything sweet"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 3,
            "hydration": -5,
            "energy": 15
        },
        "effects": ["A burst of different sweet flavors", "Purely for the joy of it"]
    },
    {
        "name": "sweet_pastry_filled",
        "descriptions": ["A sweet pastry with a cream or fruit filling", "Flaky crust, sweet inside", "Feels like a real treat"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 12,
            "hydration": -8,
            "energy": 15
        },
        "effects": ["Rich and satisfyingly sweet", "A little messy but worth it"]
    },
    {
        "name": "cola_can", # Another soda for maximum fizzy fun
        "descriptions": ["Another chilled can of fizzy cola", "Double the sugary goodness", "Just for kicks"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 3,
            "hydration": -10,
            "energy": 20
        },
        "effects": ["More bubbly goodness!", "You're definitely going to need some water after this package."]
    }
]

care_package_6_extreme_hydration = [
    {
        "name": "water_bottle_large",
        "descriptions": ["A larger-than-standard plastic water bottle", "Generous supply of clean water", "Crucial for survival"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 8,
            "hydration": 50,
            "energy": 0
        },
        "effects": ["Quenches your thirst completely", "You feel significantly more hydrated"]
    },
    {
        "name": "electrolyte_drink",
        "descriptions": ["A bottle of sports drink with electrolytes", "Helps replace lost salts and fluids", "Slightly sweet and tangy"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 40,
            "energy": 10
        },
        "effects": ["You feel instantly revitalized", "Excellent for combating dehydration and fatigue"]
    },
    {
        "name": "coconut_water_carton",
        "descriptions": ["A carton of natural coconut water", "Known for natural electrolytes and hydration", "Refreshing and slightly sweet"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 7,
            "hydration": 35,
            "energy": 5
        },
        "effects": ["A tropical burst of hydration", "Leaves you feeling naturally refreshed"]
    },
    {
        "name": "flavored_water",
        "descriptions": ["A bottle of water with a hint of fruit flavor", "Makes hydration more appealing", "Zero sugar option"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 35,
            "energy": 0
        },
        "effects": ["Plain water with a pleasant twist", "Encourages you to drink more"]
    },
    {
        "name": "cucumber",
        "descriptions": ["A crisp, cool cucumber", "Very high water content", "Refreshing and low calorie"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": 20,
            "energy": 2
        },
        "effects": ["Cooling and hydrating", "A nice watery crunch"]
    },
    {
        "name": "small_watermelon_slice",
        "descriptions": ["A juicy slice of watermelon", "Mostly water and sugar", "Sweet summer treat"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 15,
            "hydration": 30,
            "energy": 10
        },
        "effects": ["Incredibly juicy and sweet", "Perfect for rapid hydration and a little energy"]
    },
    {
        "name": "rehydration_salts_packet",
        "descriptions": ["A packet of oral rehydration salts", "Mix with water for severe dehydration", "Lifesaving in extreme heat"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 0,
            "hydration": 50, # Represents the effect when mixed with water, assumes water is available
            "energy": 5
        },
        "effects": ["Feels medically effective", "Rapidly restores hydration balance (when mixed)"]
    },
     {
        "name": "water_bottle_large", # Repeat
        "descriptions": ["Another large bottle of water", "Double the hydration capacity", "Stay quenched"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 8,
            "hydration": 50,
            "energy": 0
        },
        "effects": ["More clean water consumed", "Hydration levels are excellent"]
    }
]

care_package_7_hearty_survival_rations = [
    {
        "name": "mre_main_course_chicken",
        "descriptions": ["The main dish of a Chicken MRE", "A complete, shelf-stable meal", "Provides significant calories"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 60,
            "hydration": 10,
            "energy": 40
        },
        "effects": ["Feels like a full meal", "Provides sustained energy for hours"]
    },
    {
        "name": "mre_side_dish_potatoes",
        "descriptions": ["A side dish from an MRE, like mashed potatoes", "Adds carbs and fullness to the meal", "Usually needs heating"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 25,
            "hydration": 5,
            "energy": 15
        },
        "effects": ["Adds substance to your meal", "Carbs are good for energy"]
    },
    {
        "name": "canned_chili",
        "descriptions": ["A large can of hearty chili with beans and meat", "Spicy and filling", "Excellent comfort food in tough times"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 50,
            "hydration": 15,
            "energy": 30
        },
        "effects": ["A truly filling and warm meal", "Provides long-lasting energy and comfort"]
    },
    {
        "name": "hard_tack_biscuits",
        "descriptions": ["Extremely dense, dry biscuits", "Designed for long storage and sustenance", "Almost impossible to eat without liquid"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 30,
            "hydration": -20, # Very drying
            "energy": 15
        },
        "effects": ["Requires serious chewing", "Provides sturdy, albeit dry, sustenance"]
    },
    {
        "name": "peanut_butter_packet",
        "descriptions": ["A small packet of peanut butter", "High in fat and protein", "Excellent for quick, dense calories"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 15,
            "hydration": -10,
            "energy": 20
        },
        "effects": ["Sticky and rich", "Provides concentrated energy"]
    },
    {
        "name": "dried_fruit_mix",
        "descriptions": ["A bag of assorted dried fruits (raisins, cranberries, etc.)", "Sweet, chewy, and high in sugar/carbs", "Good energy source"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 10,
            "hydration": -5,
            "energy": 15
        },
        "effects": ["Chewy sweetness", "Provides a quick burst of sugary energy"]
    },
    {
        "name": "canned_sausages",
        "descriptions": ["Small sausages packed in brine or oil", "Salty and protein-rich", "Can be eaten cold"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 20,
            "hydration": 5,
            "energy": 15
        },
        "effects": ["Salty and savory", "A decent protein source, if not gourmet"]
    },
     {
        "name": "water_pouch", # Basic water needed with dry food
        "descriptions": ["A flexible pouch of water", "Basic hydration unit", "Functional but not fancy"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 3,
            "hydration": 25,
            "energy": 0
        },
        "effects": ["Just plain water", "Essential for washing down dry rations"]
    }
]

care_package_8_utility_mix = [
    {
        "name": "water_bottle",
        "descriptions": ["A standard plastic water bottle", "Sealed and clean", "Essential hydration"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 30,
            "energy": 0
        },
        "effects": ["Quenches your thirst effectively", "Leaves you feeling refreshed"]
    },
    {
        "name": "energy_bar",
        "descriptions": ["A high-energy snack bar", "Compact and portable", "Sweet and chewy"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": -5,
            "energy": 25
        },
        "effects": ["You feel a quick surge of energy", "It leaves a slight dryness in your mouth"]
    },
    {
        "name": "canned_soup_small",
        "descriptions": ["A small can of ready-to-eat soup", "Warm and somewhat filling", "Good for hydration and comfort"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 15,
            "hydration": 15,
            "energy": 10
        },
        "effects": ["Liquid warmth and minor sustenance", "Easy to consume"]
    },
    {
        "name": "beef_jerky_stick",
        "descriptions": ["A single stick of beef jerky", "Quick protein boost", "Satisfies savory craving"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 8,
            "hydration": -8,
            "energy": 7
        },
        "effects": ["Chewy and flavorful", "A good protein snack"]
    },
    {
        "name": "wet_wipes_pack",
        "descriptions": ["A small travel pack of wet wipes", "For basic cleaning when water is scarce", "Consumable per wipe (imagine the pack is several uses)"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 0,
            "hydration": 1, # Very minor hydration feel
            "energy": 1 # Minor morale/comfort boost
        },
        "effects": ["You feel a little cleaner", "Removes grime and sweat"]
    },
    {
        "name": "pain_reliever_packet",
        "descriptions": ["A small packet of over-the-counter pain relievers", "For headaches or minor aches", "Consumable per dose"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 0,
            "hydration": 0,
            "energy": 5 # Represents relief giving a small boost
        },
        "effects": ["Minor aches seem to subside", "You feel slightly more capable"]
    },
    {
        "name": "cracker_sandwich_pack",
        "descriptions": ["A small pack of cracker sandwiches with cheese or peanut butter filling", "More substantial than plain crackers", "Simple and portable snack"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 12,
            "hydration": -5,
            "energy": 10
        },
        "effects": ["A balanced sweet or savory snack", "Provides a little fat and carbs"]
    },
     {
        "name": "water_pouch", # Basic hydration refill
        "descriptions": ["A flexible pouch of water", "Functional hydration", "Simple water source"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 3,
            "hydration": 25,
            "energy": 0
        },
        "effects": ["More plain water", "Keeping hydrated is key"]
    }
]

care_package_9_basic_hygiene = [
    {
        "name": "toothpaste_tube_small",
        "descriptions": ["A small tube of toothpaste", "Essential for dental hygiene", "Refreshing mint flavor"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 0,
            "hydration": 2, # Minty feeling can feel slightly hydrating
            "energy": 3 # Feeling clean gives a small morale/energy boost
        },
        "effects": ["Your mouth feels clean and fresh", "Bad breath is banished for now"]
    },
    {
        "name": "toothbrush_single",
        "descriptions": ["A single-use or basic travel toothbrush", "Pairs with toothpaste for cleaning", "Simple but effective"],
        "static": False,
        "type": "consumable", # Treat as consumable per use, or perhaps it has a limited number of uses
        "stats_edit": {
            "fullness": 0,
            "hydration": 0,
            "energy": 1 # Very minor effect, mainly works with toothpaste
        },
        "effects": ["Helps scrub your teeth clean", "A necessary tool for hygiene"]
    },
    {
        "name": "bar_of_soap_travel",
        "descriptions": ["A small travel-sized bar of soap", "For washing hands and body", "Removes dirt and grime"],
        "static": False,
        "type": "consumable", # Consumed over multiple uses
        "stats_edit": {
            "fullness": 0,
            "hydration": 0,
            "energy": 5 # Feeling clean boosts morale
        },
        "effects": ["You feel noticeably cleaner", "Washes away the day's dirt"]
    },
    {
        "name": "wet_wipes_pack_large",
        "descriptions": ["A larger pack of multi-purpose wet wipes", "Useful for cleaning, hands, face, surfaces", "More uses per pack"],
        "static": False,
        "type": "consumable", # Consumed per wipe
        "stats_edit": {
            "fullness": 0,
            "hydration": 2, # Small feeling of hydration/refreshment
            "energy": 3 # Comfort/cleanliness boost
        },
        "effects": ["Quick and effective cleaning", "Makes you feel more comfortable"]
    },
     {
        "name": "hand_sanitizer_small",
        "descriptions": ["A small bottle of alcohol-based hand sanitizer", "Kills germs without water", "Alcohol smell"],
        "static": False,
        "type": "consumable", # Consumed per application
        "stats_edit": {
            "fullness": 0,
            "hydration": -1, # Alcohol can be drying
            "energy": 2 # Feeling safer/cleaner
        },
        "effects": ["Hands feel instantly clean (and dry)", "Removes worries about germs"]
    },
    {
        "name": "lip_balm",
        "descriptions": ["A small tube of lip balm", "Protects against dry, chapped lips", "Provides comfort"],
        "static": False,
        "type": "consumable", # Consumed over many uses
        "stats_edit": {
            "fullness": 0,
            "hydration": 1, # Minor feel
            "energy": 2 # Comfort/relief
        },
        "effects": ["Lips feel soft and protected", "Relieves dryness and discomfort"]
    },
    {
        "name": "dental_floss_small",
        "descriptions": ["A small dispenser of dental floss", "For cleaning between teeth", "A key part of oral hygiene"],
        "static": False,
        "type": "consumable", # Consumed per use
        "stats_edit": {
            "fullness": 0,
            "hydration": 0,
            "energy": 1 # Minor hygiene effect
        },
        "effects": ["Cleans those hard-to-reach spots", "Leaves your mouth feeling more thoroughy cleaned"]
    },
    {
        "name": "comb_small",
        "descriptions": ["A small, basic comb", "For managing hair", "Helps with basic grooming"],
        "static": False,
        "type": "consumable", # Can be seen as consumable if it breaks or is disposable
        "stats_edit": {
            "fullness": 0,
            "hydration": 0,
            "energy": 1 # Minor grooming/morale effect
        },
        "effects": ["Helps tidy up your appearance", "Feels good to manage unruly hair"]
    }
]


care_package_2_cooking_kit = [
    {
        "name": "raw_chicken_breast",
        "descriptions": ["A raw chicken breast", "Needs cooking", "Potential health risk if eaten raw"],
        "static": False,
        "type": "consumable", # Treat as consumable if eaten raw
        "stats_edit": {
            "fullness": 10,  # Might temporarily feel something in stomach
            "hydration": -15, # Digestion uses water, potential sickness causes dehydration
            "energy": -20    # Dealing with potential illness/indigestion costs energy
        },
        "effects": ["You feel a bit nauseous", "It leaves a terrible aftertaste", "Hope you don't get sick..."]
    },
    {
        "name": "raw_potato",
        "descriptions": ["A raw, starchy potato", "Hard and not very palatable raw", "Best cooked to be digestible"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 8,
            "hydration": -10, # Hard to digest dry starch
            "energy": -10     # Body struggles to process raw starch
        },
        "effects": ["It's strangely hard to chew", "Your stomach feels unsettled", "Leaves a weird taste in your mouth"]
    },
    {
        "name": "dry_rice_bag",
        "descriptions": ["A small bag of uncooked rice grains", "Needs water and heat to be edible", "Extremely hard and dry"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 1,  # Almost zero fullness
            "hydration": -30, # Severely dehydrating
            "energy": -20     # Body struggles to process, risk of damage
        },
        "effects": ["A gritty, unpleasant experience", "Leaves your mouth incredibly dry", "Feels like chewing pebbles"]
    },
    {
        "name": "raw_onion",
        "descriptions": ["A pungent, raw onion", "Very strong flavor", "Good when cooked, harsh raw"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 3,
            "hydration": 2, # Contains some water
            "energy": -5     # Unpleasantness and pungency are taxing
        },
        "effects": ["Your eyes water uncontrollably", "A strong, burning sensation on your tongue", "Not pleasant at all"]
    },
    {
        "name": "salt_packet",
        "descriptions": ["A small packet of table salt", "Essential seasoning for cooking", "Do not eat plain"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 0,   # Zero fullness
            "hydration": -40, # Massively dehydrating
            "energy": -5      # Body reacts poorly to excess sodium
        },
        "effects": ["Your mouth feels incredibly dry and burning", "You desperately need a drink immediately", "A sharp, unpleasant taste"]
    },
    {
        "name": "cooking_oil_bottle",
        "descriptions": ["A bottle of vegetable oil", "Used for frying or adding fat to dishes", "Not meant to be drunk"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5, # Might coat the stomach briefly
            "hydration": -20, # Body needs water to process fats, especially raw
            "energy": -15     # Difficult to digest raw
        },
        "effects": ["An oily, unpleasant sensation coats your mouth", "Your stomach churns uncomfortably", "Hard to swallow"]
    },
    {
        "name": "dry_beans_bag",
        "descriptions": ["A bag of hard, dry beans", "Must be soaked and cooked thoroughly", "Indigestible and potentially toxic raw"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 2,
            "hydration": -25, # Draws water from the body
            "energy": -18     # Body cannot process, risk of illness
        },
        "effects": ["Like chewing small stones", "Causes significant discomfort", "Not food in this state"]
    },
     {
        "name": "raw_eggs_carton",
        "descriptions": ["A few raw eggs in a fragile carton", "Highly nutritious when cooked", "Risk of illness if eaten raw"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 5,
            "hydration": 5, # Contains some liquid
            "energy": -25    # Significant risk of foodborne illness
        },
        "effects": ["A strange, slimy texture", "You worry about getting sick", "Hope that wasn't a mistake"]
    },
     {
        "name": "dried_herbs_mix",
        "descriptions": ["A small pouch of mixed dried herbs (e.g., oregano, basil)", "Adds flavor to cooked food", "Strong taste alone"],
        "static": False,
        "type": "consumable",
        "stats_edit": {
            "fullness": 0,
            "hydration": -2, # Slightly drying
            "energy": -2     # Not meant for direct consumption
        },
        "effects": ["An intense, slightly bitter flavor fills your mouth", "Doesn't feel like food", "Makes you want a drink"]
    }
]

# You can now access this list using the variable care_package_2_cooking_kit

a_bundle_for_hydration_some_misc_items = [{'name': 'bottle_of_water', 'descriptions': ['A refreshing bottle of clean water.'], 'static': False, 'type': 'consumable', 'effects': ['Restores hydration.'], 'stats_edit': {'fullness': 0.0, 'hydration': 20.0, 'energy': 0.0}}, {'name': 'medicinal_handkerchief', 'descriptions': ['A clean handkerchief for first aid or wiping sweat.'], 'static': True, 'type': 'misc'}, {'name': 'trail_mix', 'descriptions': ['A mix of nuts and dried fruits for quick energy.'], 'static': False, 'type': 'consumable', 'effects': ['Provides energy and sustenance.'], 'stats_edit': {'fullness': 5.0, 'hydration': 0.0, 'energy': 10.0}}]



the_most_epic_and_complete_bundle_for_cooking_raw_ = [{'name': 'raw_chicken', 'descriptions': ['Fresh raw chicken, unsafe to eat without cooking.', 'Consumption may cause severe illness.'], 'static': False, 'type': 'consumable', 'effects': ['Causes food poisoning.', 'Stomach pain.', 'Nausea.'], 'stats_edit': {'fullness': 0.5, 'hydration': -0.2, 'energy': -5.0}}, {'name': 'raw_beef', 'descriptions': ['Uncooked beef, risky to eat due to bacteria.', 'Needs thorough cooking before consumption.'], 'static': False, 'type': 'consumable', 'effects': ['Foodborne illness risk.', 'Induces cramps.', 'Vomiting.'], 'stats_edit': {'fullness': 0.7, 'hydration': -0.3, 'energy': -4.0}}, {'name': 'raw_fish', 'descriptions': ['Fresh raw fish, contains parasites if eaten uncooked.', 'Cooking required for safe eating.'], 'static': False, 'type': 'consumable', 'effects': ['May cause parasite infection.', 'Stomach cramps.', 'Dizziness.'], 'stats_edit': {'fullness': 0.6, 'hydration': -0.25, 'energy': -4.5}}, {'name': 'raw_egg', 'descriptions': ['Uncooked egg, risk of salmonella if consumed raw.', 'Must be cooked properly.'], 'static': False, 'type': 'consumable', 'effects': ['Salmonella poisoning.', 'Stomach aches.', 'Fatigue.'], 'stats_edit': {'fullness': 0.4, 'hydration': -0.15, 'energy': -3.5}}, {'name': 'raw_potato', 'descriptions': ['Raw potato, hard to digest and potentially toxic when uncooked.', 'Cooking improves digestibility.'], 'static': False, 'type': 'consumable', 'effects': ['Causes digestive discomfort.', 'Mild toxicity symptoms.', 'Nausea.'], 'stats_edit': {'fullness': 0.3, 'hydration': -0.1, 'energy': -2.0}}, {'name': 'flour', 'descriptions': ['Finely ground wheat flour, essential for baking and cooking.'], 'static': False, 'type': 'consumable', 'effects': ['Provides basic sustenance when cooked.', 'Cannot be eaten raw safely without preparation.'], 'stats_edit': {'fullness': 0.8, 'hydration': -0.05, 'energy': 3.0}}, {'name': 'raw_rice', 'descriptions': ['Uncooked rice grains, hard and unsafe to digest raw.'], 'static': False, 'type': 'consumable', 'effects': ['Causes stomach discomfort if eaten raw.', 'Must be boiled for edible consumption.'], 'stats_edit': {'fullness': 0.5, 'hydration': -0.2, 'energy': -3.0}}, {'name': 'cooking_pot', 'descriptions': ['A sturdy pot for boiling and stewing ingredients.', 'Essential for cooking raw items safely.'], 'static': False, 'type': 'misc'}, {'name': 'chef_knife', 'descriptions': ["Sharp chef's knife, perfect for chopping raw ingredients with precision.", 'A vital utensil in any kitchen.'], 'static': False, 'type': 'misc'}, {'name': 'cutting_board', 'descriptions': ['Wooden cutting board, sanitary base for chopping and preparing food.'], 'static': False, 'type': 'misc'}, {'name': 'mixing_bowl', 'descriptions': ['Large mixing bowl for combining ingredients easily.', 'Useful when preparing complex dishes.'], 'static': False, 'type': 'misc'}, {'name': 'cooking_stove', 'descriptions': ['Portable cooking stove to heat and cook raw ingredients efficiently.'], 'static': False, 'type': 'misc'}, {'name': 'measuring_cups', 'descriptions': ['Precision measuring cups for exact ingredient quantities.', 'Improves cooking accuracy.'], 'static': False, 'type': 'misc'}, {'name': 'salt', 'descriptions': ['A pinch of salt, used for seasoning dishes and preserving food.'], 'static': False, 'type': 'consumable', 'effects': ['Enhances flavor.', 'Raises thirst slightly.'], 'stats_edit': {'fullness': 0.0, 'hydration': -0.1, 'energy': 0.0}}, {'name': 'pepper', 'descriptions': ['Ground black pepper to add spice and flavor.'], 'static': False, 'type': 'consumable', 'effects': ['Increases dish spiciness.', 'May cause mild thirst.'], 'stats_edit': {'fullness': 0.0, 'hydration': -0.05, 'energy': 0.1}}, {'name': 'olive_oil', 'descriptions': ['High-quality olive oil for cooking and dressing.'], 'static': False, 'type': 'consumable', 'effects': ['Raises energy slightly.', 'Adds rich flavor.'], 'stats_edit': {'fullness': 0.1, 'hydration': 0.0, 'energy': 1.5}}, {'name': 'garlic_clove', 'descriptions': ['Fresh garlic clove, pungent and flavorful.'], 'static': False, 'type': 'consumable', 'effects': ['Boosts flavor.', 'Mild energizing effect.'], 'stats_edit': {'fullness': 0.1, 'hydration': 0.0, 'energy': 0.5}}, {'name': 'onion', 'descriptions': ['Raw onion, adds strong taste but causes eye irritation when chopped.'], 'static': False, 'type': 'consumable', 'effects': ['Strong flavor enhancement.', 'Slight eye irritation if fresh.'], 'stats_edit': {'fullness': 0.2, 'hydration': 0.0, 'energy': 0.3}}, {'name': 'fresh_herbs_bundle', 'descriptions': ['A bundle of fresh herbs like thyme, rosemary, and parsley.', 'Adds aroma and flavor to dishes.'], 'static': False, 'type': 'consumable', 'effects': ['Improves the taste and aroma of food.'], 'stats_edit': {'fullness': 0.1, 'hydration': 0.0, 'energy': 0.2}}]


a_bundle_for_energy_and_snacks = [{'name': 'energy_bar', 'descriptions': ['A compact bar loaded with nuts and dried fruits to boost your energy quickly.', 'Convenient snack for on-the-go energy replenishment.'], 'static': False, 'type': 'consumable', 'effects': ['Instant energy boost', 'Satisfies hunger moderately'], 'stats_edit': {'fullness': 5.0, 'hydration': 0.0, 'energy': 15.0}}, {'name': 'fruit_juice_bottle', 'descriptions': ['A refreshing bottle of mixed fruit juice packed with natural sugars and vitamins.', 'Great for hydration and quick energy.'], 'static': False, 'type': 'consumable', 'effects': ['Rehydrates and energizes', 'Lightly satisfies hunger'], 'stats_edit': {'fullness': 2.0, 'hydration': 12.0, 'energy': 8.0}}, {'name': 'mixed_nuts_packet', 'descriptions': ['A small packet of mixed nuts providing proteins and healthy fats.', 'Perfect for a crunchy, satisfying snack.'], 'static': False, 'type': 'consumable', 'effects': ['Good source of energy', 'Fills you up a little'], 'stats_edit': {'fullness': 7.0, 'hydration': 0.0, 'energy': 10.0}}, {'name': 'granola_bar', 'descriptions': ['A granola bar made of oats, honey and seeds, perfect for a sustained energy release.', 'Ideal for a quick snack while working or traveling.'], 'static': False, 'type': 'consumable', 'effects': ['Sustained energy release', 'Moderate hunger satisfaction'], 'stats_edit': {'fullness': 6.0, 'hydration': 0.0, 'energy': 12.0}}]


a_bundle_for_outdoor_survival = [{'name': 'water_bottle', 'descriptions': ['A durable bottle filled with clean water to keep you hydrated.'], 'static': False, 'type': 'consumable', 'effects': ['Hydrates the body, preventing dehydration.'], 'stats_edit': {'fullness': 0.0, 'hydration': 10.0, 'energy': 0.0}}, {'name': 'energy_bar', 'descriptions': ['A compact bar packed with nutrients and energy.'], 'static': False, 'type': 'consumable', 'effects': ['Boosts energy levels and satisfies hunger.'], 'stats_edit': {'fullness': 5.0, 'hydration': 0.0, 'energy': 8.0}}, {'name': 'fire_starter_kit', 'descriptions': ['A small kit containing flint and steel to start fires quickly.'], 'static': False, 'type': 'misc'}, {'name': 'pocket_knife', 'descriptions': ['A multipurpose folding knife useful for cutting and preparing materials.'], 'static': False, 'type': 'misc'}, {'name': 'first_aid_kit', 'descriptions': ['A compact set of medical supplies for treating minor injuries.'], 'static': False, 'type': 'misc'}]


kitchen_pantry_bottled_goods_spices_etc_all_consum = [{'name': 'olive_oil_bottle', 'descriptions': ['A 500ml bottle of extra virgin olive oil, perfect for cooking and dressing salads.'], 'static': False, 'type': 'consumable', 'effects': ['Adds rich flavor and healthy fats to your meals.'], 'stats_edit': {'fullness': 0.0, 'hydration': 0.0, 'energy': 5.0}}, {'name': 'black_pepper_grinder', 'descriptions': ['A small grinder filled with freshly ground black peppercorns, enhancing your dishes with spicy warmth.'], 'static': False, 'type': 'consumable', 'effects': ['Enhances flavor with a mild heat.'], 'stats_edit': {'fullness': 0.0, 'hydration': 0.0, 'energy': 1.0}}, {'name': 'dried_basil', 'descriptions': ['A small jar of dried basil leaves, adding a sweet, aromatic flavor to Mediterranean dishes.'], 'static': False, 'type': 'consumable', 'effects': ['Imparts a fragrant, herbal taste to recipes.'], 'stats_edit': {'fullness': 0.0, 'hydration': 0.0, 'energy': 0.5}}, {'name': 'canned_tomato_puree', 'descriptions': ['A can of tomato puree, thick and rich, perfect for sauces and stews.'], 'static': False, 'type': 'consumable', 'effects': ['Provides a tangy, umami base for various dishes.'], 'stats_edit': {'fullness': 3.0, 'hydration': 2.5, 'energy': 4.0}}, {'name': 'honey_jar', 'descriptions': ['A small jar of natural honey, sweet and viscous, excellent as a sweetener or glaze.'], 'static': False, 'type': 'consumable', 'effects': ['Sweetens dishes naturally while boosting energy.'], 'stats_edit': {'fullness': 1.0, 'hydration': 0.0, 'energy': 8.0}}, {'name': 'white_vinegar', 'descriptions': ['A clear bottle of white vinegar, sharp and tangy, used for pickling and cleaning.'], 'static': False, 'type': 'consumable', 'effects': ['Adds acidity and brightness to recipes.'], 'stats_edit': {'fullness': 0.0, 'hydration': 0.0, 'energy': -1.0}}, {'name': 'sea_salt_container', 'descriptions': ['A container filled with coarse sea salt crystals, essential for seasoning.'], 'static': False, 'type': 'consumable', 'effects': ['Enhances flavor and balances sweetness.'], 'stats_edit': {'fullness': 0.0, 'hydration': 0.0, 'energy': 0.0}}, {'name': 'cinnamon_sticks', 'descriptions': ['A bundle of cinnamon sticks, warming and sweetly spicy.'], 'static': False, 'type': 'consumable', 'effects': ['Adds warm, sweet spice to drinks and desserts.'], 'stats_edit': {'fullness': 0.0, 'hydration': 0.0, 'energy': 1.5}}, {'name': 'chili_flakes', 'descriptions': ['A jar of dried chili flakes for adding heat and spice to dishes.'], 'static': False, 'type': 'consumable', 'effects': ['Introduces a sharp, spicy kick.'], 'stats_edit': {'fullness': 0.0, 'hydration': 0.0, 'energy': 2.0}}, {'name': 'garlic_powder', 'descriptions': ['A small jar of finely ground garlic powder for savory flavoring.'], 'static': False, 'type': 'consumable', 'effects': ['Imparts robust garlic flavor to cooked dishes.'], 'stats_edit': {'fullness': 0.0, 'hydration': 0.0, 'energy': 1.0}}]


salty_and_hardy_foods = [{'name': 'salted_beef_jerky', 'descriptions': ['Dried strips of beef preserved with salt.', 'A tough, chewy snack rich in protein.'], 'static': False, 'type': 'consumable', 'effects': ['Restores stamina quickly due to high sodium and protein content.'], 'stats_edit': {'fullness': 12.0, 'hydration': -6.0, 'energy': 18.0}}, {'name': 'salted_potato_crisps', 'descriptions': ['Thinly sliced potatoes fried and salted.', 'Crunchy and savory snack perfect for quick energy.'], 'static': False, 'type': 'consumable', 'effects': ['Gives a quick burst of energy with a salty tang.'], 'stats_edit': {'fullness': 8.0, 'hydration': -3.5, 'energy': 15.0}}, {'name': 'hardy_raw_cheese', 'descriptions': ['A dense, aged cheese with a strong flavor.', 'Needs to be cooked or properly cured before eating.'], 'static': False, 'type': 'consumable', 'effects': ['Can be harsh on the stomach if eaten raw, causing discomfort.'], 'stats_edit': {'fullness': 10.0, 'hydration': -2.0, 'energy': 7.0}}, {'name': 'salted_nuts_mix', 'descriptions': ['A mixture of assorted nuts roasted and salted.', 'Rich in fats and protein, ideal for a hearty snack.'], 'static': False, 'type': 'consumable', 'effects': ['Provides lasting energy and fullness, but can cause thirst.'], 'stats_edit': {'fullness': 15.0, 'hydration': -4.5, 'energy': 20.0}}, {'name': 'hardy_dried_fish', 'descriptions': ['Salt-cured and dried fish with a chewy texture.', 'High in protein and salt content.'], 'static': False, 'type': 'consumable', 'effects': ['Replenishes energy with a strong salty taste.', 'May cause slight dehydration.'], 'stats_edit': {'fullness': 14.0, 'hydration': -5.0, 'energy': 22.0}}, {'name': 'salt_crystals', 'descriptions': ['Coarse grains of pure salt.', 'Essential for preserving and enhancing flavor.'], 'static': False, 'type': 'misc'}]


fresh_vegetables = [{'name': 'carrot', 'descriptions': ['A fresh, crunchy orange carrot.', 'Great for snacking or cooking.', 'Rich in vitamins and fiber.'], 'static': False, 'type': 'consumable', 'effects': ['Restores a small amount of energy.', 'Increases fullness slightly.'], 'stats_edit': {'fullness': 8.0, 'hydration': 0.1, 'energy': 5.0}}, {'name': 'cucumber', 'descriptions': ['A cool, crisp cucumber.', 'Perfect for hydration and light snacks.', 'Offers a refreshing taste.'], 'static': False, 'type': 'consumable', 'effects': ['Greatly increases hydration.', 'Slightly restores energy.'], 'stats_edit': {'fullness': 5.0, 'hydration': 18.0, 'energy': 3.0}}, {'name': 'tomato', 'descriptions': ['A ripe, juicy tomato.', 'Good source of vitamins and antioxidants.', 'Adds a burst of flavor to dishes.'], 'static': False, 'type': 'consumable', 'effects': ['Moderate increase in fullness and hydration.', 'Restores some energy.'], 'stats_edit': {'fullness': 10.0, 'hydration': 12.0, 'energy': 4.0}}, {'name': 'bell_pepper', 'descriptions': ['A colorful bell pepper, crunchy and sweet.', 'Rich in vitamin C.', 'Brightens up any salad or meal.'], 'static': False, 'type': 'consumable', 'effects': ['Restores energy and fullness moderately.', 'Slight hydration boost.'], 'stats_edit': {'fullness': 9.0, 'hydration': 6.0, 'energy': 6.0}}, {'name': 'fresh_spinach', 'descriptions': ['Leafy fresh spinach, packed with nutrients.', 'Great for salads or cooking.', 'Boosts energy and vitality.'], 'static': False, 'type': 'consumable', 'effects': ['Increases energy significantly.', 'Moderate fullness and hydration effects.'], 'stats_edit': {'fullness': 7.0, 'hydration': 9.0, 'energy': 15.0}}]


bread_package_all_kinds_of_food_implements_ingredi = [{'name': 'bread_loaf', 'descriptions': ['A freshly baked loaf of bread with a golden crust and soft interior.', 'Perfect for sandwiches or just enjoying with butter.'], 'static': False, 'type': 'consumable', 'effects': ['Restores a moderate amount of fullness.', 'Gives a comforting, homely feeling.'], 'stats_edit': {'fullness': 15.0, 'hydration': -1.5, 'energy': 10.0}}, {'name': 'mixing_bowl', 'descriptions': ['A large ceramic mixing bowl used for combining ingredients.', 'Sturdy and easy to clean.'], 'static': False, 'type': 'misc'}, {'name': 'wooden_spoon', 'descriptions': ['A classic wooden spoon for stirring and mixing.', 'Smooth and durable.'], 'static': False, 'type': 'misc'}, {'name': 'measuring_cups_set', 'descriptions': ['A set of nesting measuring cups for precise baking.', 'Includes multiple sizes for all your ingredient needs.'], 'static': False, 'type': 'misc'}, {'name': 'flour_bag', 'descriptions': ['A bag of finely milled white flour.', 'A fundamental ingredient for breads and cakes.'], 'static': False, 'type': 'consumable', 'effects': ['Used as a base for baking various breads and pastries.'], 'stats_edit': {'fullness': 2.0, 'hydration': 0.0, 'energy': 5.0}}, {'name': 'yeast_packet', 'descriptions': ['A small packet of active dry yeast.', 'Essential for making bread rise and giving it a fluffy texture.'], 'static': False, 'type': 'misc'}, {'name': 'sugar_pouch', 'descriptions': ['A small pouch of granulated sugar.', 'Used to sweeten cakes and baked goods.'], 'static': False, 'type': 'consumable', 'effects': ['Adds sweetness when cooking or baking.'], 'stats_edit': {'fullness': 1.0, 'hydration': 0.0, 'energy': 8.0}}, {'name': 'butter_pack', 'descriptions': ['A block of creamy butter.', 'Adds richness and flavor to breads and cakes.'], 'static': False, 'type': 'consumable', 'effects': ['Enhances taste and texture of baked goods.'], 'stats_edit': {'fullness': 4.0, 'hydration': 0.0, 'energy': 12.0}}, {'name': 'oven_mitts', 'descriptions': ['Thick insulating oven mitts for safe handling of hot baking dishes.', 'Protects your hands from heat.'], 'static': False, 'type': 'misc'}, {'name': 'cake_pan', 'descriptions': ['A round cake pan, perfect for baking cakes and other desserts.', 'Non-stick surface for easy release.'], 'static': False, 'type': 'misc'}]


raw_protein_package = [{'name': 'uncooked_chicken_breast', 'descriptions': ['Raw chicken breast, rich in protein but requires cooking before consumption.'], 'static': False, 'type': 'consumable', 'effects': ['Consuming raw chicken breast may cause food poisoning.'], 'stats_edit': {'fullness': 5.0, 'hydration': 0.0, 'energy': -10.0}}, {'name': 'raw_ground_beef', 'descriptions': ['Fresh ground beef, high in protein and fats, needs cooking.'], 'static': False, 'type': 'consumable', 'effects': ['Eating raw ground beef risks bacterial infection.'], 'stats_edit': {'fullness': 6.0, 'hydration': 0.0, 'energy': -8.0}}, {'name': 'uncooked_egg', 'descriptions': ['A fresh egg in shell, full of protein and nutrients, must be cooked.'], 'static': False, 'type': 'consumable', 'effects': ['Raw eggs may cause salmonella infection if consumed without cooking.'], 'stats_edit': {'fullness': 2.0, 'hydration': 0.0, 'energy': -5.0}}, {'name': 'raw_tofu_block', 'descriptions': ['Uncooked tofu block made from soybeans, high protein plant-based item.'], 'static': False, 'type': 'consumable', 'effects': ['Raw tofu is safe but bland until cooked.'], 'stats_edit': {'fullness': 4.0, 'hydration': 0.5, 'energy': 2.0}}, {'name': 'raw_salmon_fillet', 'descriptions': ['Raw salmon fillet, rich in omega-3 and protein, usually cooked or prepared as sushi.'], 'static': False, 'type': 'consumable', 'effects': ['Consuming raw salmon may cause parasites or food poisoning.'], 'stats_edit': {'fullness': 5.5, 'hydration': 0.0, 'energy': -7.0}}]


more_raw_protein_package = [{'name': 'raw_chicken', 'descriptions': ['A whole uncooked chicken, fresh but raw and potentially dangerous to eat without cooking.'], 'static': False, 'type': 'consumable', 'effects': ['Eating raw chicken can cause severe stomach ache, nausea, and dehydration.'], 'stats_edit': {'fullness': -10.0, 'hydration': -30.0, 'energy': -50.0}}, {'name': 'raw_steak', 'descriptions': ['A thick cut of raw beef steak, fresh but not suitable for eating without cooking.'], 'static': False, 'type': 'consumable', 'effects': ['Consuming raw steak may cause food poisoning, resulting in loss of appetite, dehydration, and low energy.'], 'stats_edit': {'fullness': -8.0, 'hydration': -25.0, 'energy': -40.0}}, {'name': 'raw_salmon', 'descriptions': ['A raw piece of salmon, oily and fresh but risky to eat uncooked.'], 'static': False, 'type': 'consumable', 'effects': ['Eating raw salmon might cause digestive upset and dehydration.'], 'stats_edit': {'fullness': -5.0, 'hydration': -20.0, 'energy': -30.0}}, {'name': 'raw_egg', 'descriptions': ['A fresh egg in its shell, raw and potentially hazardous to eat raw.'], 'static': False, 'type': 'consumable', 'effects': ['Raw eggs can cause stomach cramps and slight dehydration.'], 'stats_edit': {'fullness': -3.0, 'hydration': -10.0, 'energy': -15.0}}, {'name': 'raw_pork_chop', 'descriptions': ['An uncooked pork chop, risky to consume without proper cooking.'], 'static': False, 'type': 'consumable', 'effects': ['Eating raw pork may lead to foodborne illness with symptoms including stomach pain and weakness.'], 'stats_edit': {'fullness': -7.0, 'hydration': -22.0, 'energy': -35.0}}]



############


spaceship_items = [{'name': 'space_ration_pack', 'descriptions': ['A compact pack of nutritious space rations designed to sustain astronauts on long missions.', 'Includes freeze-dried fruits, nuts, and protein bars.'], 'static': False, 'type': 'consumable', 'effects': ['Restores moderate fullness and energy.', 'Light hydration benefits due to moisture content.'], 'stats_edit': {'fullness': 20.0, 'hydration': 10.0, 'energy': 15.0}}, {'name': 'oxygen_tank', 'descriptions': ['A portable oxygen tank used to provide breathable air in low-oxygen environments.', 'Essential for spacewalks and emergencies.'], 'static': False, 'type': 'misc},{', 'effects': None, 'stats_edit': None}, {'name': 'zero_g_toolkit', 'descriptions': ['A set of tools designed for use in zero gravity environments.', 'Includes wrenches, screwdrivers, and specialized instruments.'], 'static': False, 'type': 'misc'}, {'name': 'raw_space_protein', 'descriptions': ['Uncooked protein source intended for consumption after proper preparation.', 'Consuming raw protein causes illness and energy loss.'], 'static': False, 'type': 'consumable', 'effects': ['Causes stomach ache, dehydration, and sickness.', 'Reduces energy severely if consumed raw.'], 'stats_edit': {'fullness': -10.0, 'hydration': -30.0, 'energy': -50.0}}, {'name': 'space_canteen', 'descriptions': ['A reusable canteen designed to store and purify water in space.', 'Ensures hydration on long missions.'], 'static': False, 'type': 'misc'}, {'name': 'energy_capsule', 'descriptions': ['A high-tech capsule that instantly boosts energy levels.', 'Used by astronauts to maintain focus during critical tasks.'], 'static': False, 'type': 'consumable', 'effects': ['Provides a significant energy boost.', 'Slightly increases fullness.'], 'stats_edit': {'fullness': 5.0, 'hydration': 0.0, 'energy': 40.0}}, {'name': 'emergency_med_kit', 'descriptions': ['A compact medical kit containing essential supplies for treating minor injuries and illnesses in space.'], 'static': False, 'type': 'misc'}]
