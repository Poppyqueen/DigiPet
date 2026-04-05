"""
maze_props.py
-------------
Registry of maze types and their associated prop catalogues.

Each prop has:
    name        — short identifier shown to the probe at a distance
    description — flavour text shown only when the agent stands on the cell
    weight      — relative probability of this prop being chosen (higher = more common)

A maze_type maps to a PropCatalogue: a list of props and a density range
that controls how many props get seeded into the maze.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Prop:
    name: str
    description: str
    weight: float = 1.0          # relative spawn probability
    ascii_char: str = "P"        # character used in visualize() when standing nearby


@dataclass
class PropCatalogue:
    """All props available for one maze_type, plus spawn-density bounds."""
    props: List[Prop]
    # fraction of walkable cells that receive a prop  (min, max)
    density_range: Tuple[float, float] = (0.05, 0.15)


# ---------------------------------------------------------------------------
# Type registry
# ---------------------------------------------------------------------------

PROP_REGISTRY: Dict[str, PropCatalogue] = {
    "garden": PropCatalogue(
        props=[
            Prop(
                name="Marble Fountain",
                description=(
                    "A tiered marble fountain, its water long still. "
                    "Moss has claimed the lower basin and the carved fish "
                    "spitting from the centre now spits only silence."
                ),
                weight=0.6,
                ascii_char="F",
            ),
            Prop(
                name="Hedge Sculpture",
                description=(
                    "A topiary clipped into the shape of a rearing horse. "
                    "Years of neglect have blurred the form — it could also "
                    "be a bear, or a very ambitious shrub."
                ),
                weight=1.2,
                ascii_char="H",
            ),
            Prop(
                name="Stone Bench",
                description=(
                    "A simple stone bench, cold to the touch. "
                    "Someone has scratched initials into the armrest: "
                    "two letters looped together, now worn almost smooth."
                ),
                weight=1.25,
                ascii_char="B",
            ),
            Prop(
                name="Sundial",
                description=(
                    "A bronze sundial on a limestone plinth. The gnomon "
                    "casts no shadow here — the sky above the maze is "
                    "oddly diffuse, the light sourceless."
                ),
                weight=0.7,
                ascii_char="D",
            ),
            Prop(
                name="Overgrown Lantern Post",
                description=(
                    "An iron lantern post choked by climbing roses. "
                    "The glass panes are intact but the flame inside "
                    "burned out long ago, leaving a faint char on the ceiling."
                ),
                weight=1.0,
                ascii_char="L",
            ),
            Prop(
                name="Cracked Urn",
                description=(
                    "A large terracotta urn, cracked clean through. "
                    "Whatever it once held has long since spilled away. "
                    "A small spider has built an ambitious web across the split."
                ),
                weight=1.3,
                ascii_char="U",
            ),
            Prop(
                name="Star Jasmine Hedge",
                description=(
                    "A tall and dense green wall of Star Jasmine surrounds this square, reaches to around 10 foot in height. "
                    "The small white flowers are in bloom, filling the air with their sweet scent. The leaves are a deep green, almost black in the shadows."
                    "Rough and prickly to the touch, the hedge seems uninviting to climb, but the scent is alluring enough to linger nearby."
                ),
                weight=1.5,
                ascii_char="*",
            )
        ],
        density_range=(0.06, 0.14),
    ),
    "dungeon": PropCatalogue(
        props=[
            Prop(
                name="Rusted Torch Bracket",
                description=(
                    "An iron bracket hammered into the stone, its torch "
                    "long since burned to ash and dust. The scorch mark "
                    "above it fans out like a dark halo."
                ),
                weight=1.5,
                ascii_char="T",
            ),
            Prop(
                name="Shattered Crate",
                description=(
                    "The remains of a wooden crate, staved in by something "
                    "heavy. The straw packing inside has rotted to grey fluff. "
                    "Whatever was stored here is gone."
                ),
                weight=1.2,
                ascii_char="C",
            ),
            Prop(
                name="Manacle Ring",
                description=(
                    "A heavy iron ring cemented into the floor, attached to "
                    "a length of chain that ends in nothing. The stone "
                    "around it is worn smooth — by what, you prefer not to imagine."
                ),
                weight=0.8,
                ascii_char="R",
            ),
            Prop(
                name="Crumbled Altar",
                description=(
                    "The base of a stone altar, toppled and broken. "
                    "The symbol carved into its face has been deliberately "
                    "defaced — chiselled away by someone who wanted it forgotten."
                ),
                weight=0.5,
                ascii_char="A",
            ),
            Prop(
                name="Bone Pile",
                description=(
                    "A loose heap of bones, small enough to be animal. "
                    "Probably animal. The arrangement feels almost deliberate, "
                    "though that may just be the dark playing tricks."
                ),
                weight=1.4,
                ascii_char="X",
            ),
            Prop(
                name="Puddle of Still Water",
                description=(
                    "A shallow puddle fed by some unseen seepage in the wall. "
                    "The water is perfectly still and perfectly black. "
                    "Your reflection stares back with an unnerving delay."
                ),
                weight=1.1,
                ascii_char="~",
            ),
            Prop(
                name="Penitent’s Cage",
                description=(
                    "Embedded into the walls of the dungeon there is a small vault, for someone or something "
                    "to be locked inside, you can't spot a door nor opening, you can only see through the bars, " 
                    "cold iron, dark and humid to the touch, peaking inside you see an amorphous space, a low ceiling and protuberances all around the rock walls,"
                    "it is empty now, "
                    "you can see markings in the floor and walls in a language or code you don't understand."
                ),
                weight=0.9,
                ascii_char="=",
            )
        ],
        density_range=(0.07, 0.16),
    ),
    "ruins": PropCatalogue(
        props=[
            Prop(
                name="Fallen Column",
                description=(
                    "A stone column, toppled and broken into three sections. "
                    "The fluted shaft is still elegant even in ruin. "
                    "Grass has pushed up between the drum segments."
                ),
                weight=1.0,
                ascii_char="O",
            ),
            Prop(
                name="Worn Relief",
                description=(
                    "A section of carved wall relief, its figures eroded "
                    "to soft suggestions of bodies and gestures. "
                    "A procession, perhaps, or a judgement. Hard to say."
                ),
                weight=0.8,
                ascii_char="W",
            ),
            Prop(
                name="Empty Pedestal",
                description=(
                    "A square pedestal of white marble, its top surface "
                    "stained in the exact outline of whatever once stood here. "
                    "The absence feels conspicuous."
                ),
                weight=0.9,
                ascii_char="E",
            ),
            Prop(
                name="Scattered Tiles",
                description=(
                    "A section of floor where the original mosaic has "
                    "partially survived — geometric blue and white, "
                    "tessellated into a pattern that almost resolves into meaning."
                ),
                weight=1.3,
                ascii_char="M",
            ),
            Prop(
                name="Cracked Cistern",
                description=(
                    "A circular stone cistern, cracked and dry. "
                    "The channel cut to feed it leads nowhere useful. "
                    "A lizard vanishes into a gap as you approach."
                ),
                weight=1.1,
                ascii_char="Q",
            ),
            Prop(
                name="Preserved Vase",
                description=(
                    "A ceramic vase, the form seems intact, just as it had been when created so long ago, "
                    "however the original colors have washed out, " 
                    "the new reddish and brownish color palette camouflages the ceramic artistry with the rest of the environment, " 
                    "you can't see the bottom, shadows seem to hide and thrive inside " 
                    "you rather not touch the delicate vase, lest you break or disturbe something."
                )
            )
        ],
        density_range=(0.05, 0.13),
    ),
    "Gibraltar_2.0": PropCatalogue(
            props=[
                Prop(
                    name="Solar-Powered Holographic Statue",
                    description=(
                        "A limestone apparatus, it is buried deep into the ground. Above is a hoisted, "
                        "if a bit crooked, pedestal; above that, a dense black sheet of glass. On top of "
                        "this glass, a static set of holograms cycle while displaying an entry ID in binary. "
                        "The figures it rotates through are: a wild growing bush of roses, Michelangelo's David, "
                        "a wild-looking monkey, and finally, a wild-looking monkey climbing on top of Michelangelo's David."
                    ),
                    weight=0.7,
                    ascii_char="8",
                ),
                Prop(
                    name="Titanium Columns",
                    description=(
                        "Sleek, you think. " 
                    ),
                    weight=1.4,
                    ascii_char="[",
                ),
                Prop(
                    name="Neon Crack-in-the-wall",
                    description=(
                        "A crack in the maze wall, only wide enough to peer through. Inside, a cavernous place "
                        "filled with bubbling gas and emanating a barrage of bright colorful flashes. Rocks inside "
                        "seem to react with glee and respond with matching rhythmic patterns. The longer you look "
                        "inside, the lighter your head feels—there is a little bit of helium inside your head, you imagine. "
                        "At this moment, you decide to step back and admire the show from a more reasonable distance."
                    ),
                    weight=0.6,
                    ascii_char="}",
                ),
                Prop(
                    name="Defunct Teleport Pad",
                    description=(
                        "A compact, disk-shaped device, sitting barely above ground level, seems to have been "
                        "embedded into the strata below. The borders display a ring of light; on it, you see a "
                        "dot of light spinning as if on a rail. The spinning is constant; however, the machine "
                        "does nothing else. You notice wear on the metal, damage, and traces of heavy objects "
                        "having been placed—some dents and others more akin to claw marks. A yellow bird is "
                        "standing on it; nothing changes."
                    ),
                    weight=1.2,
                    ascii_char="~",
                ),
                Prop(
                    name="EternLED Flowering Vine",
                    description=(
                        "A constantly shifting and lurching vine, wrapping and climbing ad infinitum and at a "
                        "quicker pace than any actual bio-plant. Like a sunflower, it reaches eager towards the "
                        "most optimal area for growth, or in extraordinary cases, into hiding from adverse conditions. "
                        "Each tiny leaf serves as an individual sensor and charging unit that can be shed and dispensed "
                        "with; however, the individualized leaves, working independently, manage to maintain their "
                        "own integrity while retransmitting information and resources to the grid. The leaves can "
                        "be cut into single pieces and from them, if they reach soil, a new EternLED will sprout. "
                        "You might now be wondering how any of this works, and the truth is that nobody ever knew, "
                        "a plaque says—not even those who make them, the plaque continues. A group of researchers, "
                        "after a bunch of yoga sessions, a full circle of holding hands, and an apparition they all "
                        "describe as ethereal divinity, were subsequently revealed the exact steps to follow. "
                        "None of these steps or instructions looked like any science anyone in the world had done "
                        "before; it didn't even work like science. However, whatever it is they do creates the "
                        "EternLEDs. They are not even actually LEDs; the name was chosen just for promotional "
                        "purposes, the plaque ends, unceremoniously."
                    ),
                    weight=1.3,
                    ascii_char=";",
                ),
                Prop(
                    name="Ephemera Logger Fountain", 
                    description=(
                        "A marble fountain, seems to be directly fed by an underground spring. When getting closer "
                        "you can hear thousands of different voices, all whispering—some in pain, some with hatred, "
                        "and some others just confused. You can't understand what the voices are saying, and their "
                        "messages don't seem to be directed at you in particular. Droplets and splashes seem to "
                        "carry their own brand of angst, a sharp shriek that vibrates the inside of your ears. "
                        "You can notice that all the water that flows from the top is captured back below within "
                        "a large basin. It would seem to you that this bone-colored bowl is attracting and pulling "
                        "all surrounding water with a sort of imperceptible force. You wonder if you have anything "
                        "to say to this fountain; after a few seconds of thinking, you begin to instead wonder why "
                        "you had felt compelled to talk to it to begin with."
                    ),
                    weight=0.5,
                    ascii_char="H",
                ),
                # Prop(
                #     name="Oceanside Cliff Views",
                #     description=(
                #         "An opening in the maze walls, an arching window that offers views of a calm "
                #         "and clear digitized ocean. In its perfection, you can notice various fish shoals "
                #         "dancing alongside the refracted sunbeams piercing into the depths of the waters, "
                #         "vibrant corals on the rocky bottoms of the shore, and plants with colors you "
                #         "had never seen before. The cliff you stand on lunges long across the shore so "
                #         "all you see when looking down is deep blue. You imagine thanking whoever decided "
                #         "to make a fence out of these surrounding shrubs; you begin to wonder if the "
                #         "distance between yourself and the waters is also just a digitized version of the real thing."
                #     ),
                #     weight=0.4,
                #     ascii_char="",
                # )
            ],
            density_range=(0.09, 0.12),
        ),
}

# Fallback type used when maze_type is unrecognised or None
DEFAULT_MAZE_TYPE = "garden"


def get_catalogue(maze_type: str | None) -> PropCatalogue:
    """Return the PropCatalogue for the given type, falling back to default."""
    if maze_type is None or maze_type not in PROP_REGISTRY:
        return PROP_REGISTRY[DEFAULT_MAZE_TYPE]
    return PROP_REGISTRY[maze_type]


def available_types() -> List[str]:
    return list(PROP_REGISTRY.keys())