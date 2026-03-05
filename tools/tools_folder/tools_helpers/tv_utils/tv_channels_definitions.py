# TV types live here, they define:

# - The name of the TV type, used in TV item data structure, reference this for creation of TVs
# - The channels that exist on that TV type, used for agent and GUI access
# - The description of each channel, used for agent and GUI access
# - The extra prompt for each channel (optional), used for AI generation of content

TV_TYPE_CHANNELS: dict[str, list[dict]] = {
    "standard": [
        {"name": "Channel 1 - News", "description": "Local and world news coverage"},
        {"name": "Channel 2 - Sports", "description": "Live sports and highlights"},
        {"name": "Channel 3 - Drama", "description": "Prime time drama series"},
        {"name": "Channel 4 - Comedy", "description": "Sitcoms and stand-up specials"},
        {"name": "Channel 5 - Nature", "description": "Wildlife and nature documentaries"},
    ],
    "bad tv": [
        {"name": "Channel 1 - News", "description": "Local and world news coverage", "extra_prompt": "A news channel, this show has 3 hosts, they sit in a row, crammed in a small anchor desk for-two-thin-men. The 3 hosts are varying in weight and they are ordered, sitting by height from tallest to shortest. The middle one, and heaviest, wears various hats, (the hats are always new to the viewer, like that french beret they wore yesterday's night, with fantasy pom-pom balls made out of random strands of colorful yarn in purple and green tones.), of different colors and shapes each day, sometimes changing them in between segments. They concern themselves with the daily news-stream of the world and local random events alongside breaking news, incompetently reporting on them by missing crucial details, misinterpreting events, and misconstruing facts. The diverse and constant non sequitur events in the show serve to confuse and at a point worry the audience."},
        {"name": "Channel 2 - Sports", "description": "Live sports and highlights", "extra_prompt": "A bureaucratic sports news channel, commentators sit with a large distance between them, they are very serious and formal, conversations usually drift into dry statistics and oddly, sometimes into the personal lives (sometimes melodramatic, sometimes bizarre and often loaded with unwarranted details) of the commentators."},
        {"name": "Channel 3 - Love Hearts", "description": "Drama, love, and men; the channel for you.", "extra_prompt": "A melodramatic and soapy channel, mostly romance and family drama. English dubbed Telenovelas sometimes air here. The lives of the poor, the unwanted, those in love, the unberevably sad ones, and others; all sharing a love for constant state of innaction, wallow, and the idea of their saviors."},
        {"name": "Channel 4 - Comedy", "description": "Sitcoms and stand-up specials", "extra_prompt": "'Lowbrow, corny, and uninspired sitcoms, stand-up series and movies.', the channel. It is not very popular. Tries to toe a line between family friendly and adult humor with attempted subtlety on blue comedy or 'ribaldry', constantly flailing uncomfortably with both. It shares the same laugh track with all its shows. Their shows have a narrow range of slice of life live-action sitcoms featuring families, groups of friends, co-workers, and other social groups."},
        {"name": "Channel 5 - Nature", "description": "Wildlife and nature documentaries", "extra_prompt": "Long winded wildlife documentaries, with choppy editing, amateur camera work, sometimes they try passing city parks recordings as wilderness scenes, only to be given away by the presence of rogue people in the background, the hidden backdrop of the city's skyline, and the passing by dogs in the supposed deep jungles. The narration is constantly interrupted by the speaker leaving for a drink, or getting a phone alert. There was this time where the network broadcasted a the visuals for a documentary on dinosaurs, but the narration was about the history of the network, and the people who worked there. There was this other case where they mixed up the images for 'The history of Hippos in Africa' with the audio of that dramatization of the Book of Revelation. That dramatization was made as an special event that the network decided to air, but it was still being broadcasted alongside the regular programming."},
    ]
    # ,
    # "90s TV":
    # [
    #     {
    #         "name": "WB Flash News",
    #         "description": "Era 90s news coverage, fast pased, 'The here, now'. A modern take on news for a young adults audience."
    #     },
    #     {
    #         "name": "HBU Drama Central",
    #         "description": "An aclaimed hub for post-modern, cinematic serialized dramas."
    #     },
    #     {
    #         "name": "NAA Sports Zone",
    #         "description": ""
    #     },
    #     {
    #         "name": "MBT Music Broadcast Trade",
    #         "description": "Music focused channel, featuring flashy and scandalous music videos."
    #     },
    #     {
    #         "name": "Sci-Fi Channel",
    #         "description": "Series and movies, classic sci-fi and fantasy narratives, epic space operas, and mind-bending adventures."
    #     },
    #     {
    #         "name": "PaperMache Network",
    #         "description": "Cartoons, animation, and children's programming."
    #     }
    # ],
}