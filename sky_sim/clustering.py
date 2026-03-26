import math
from dataclasses import dataclass, field
from collections import Counter
from typing import List, Tuple
from .types import StarResult
# This needs close attention.

# Not sure my understanding of it it correct nor how to correctly improve it.
# I like what it does already, however, it is like chasing a wild goose, but there are some highlights that reflect historical accounts of human perception of astro objects, this is great, but it breaks down in some cases

@dataclass
class StarCluster:
    stars: List[StarResult]
    leads: List[StarResult]
    center_az: float
    center_alt: float
    width: float
    height: float

    @property
    def total_count(self) -> int:
        return len(self.stars)


def angular_distance(s1_az, s1_alt, s2_az, s2_alt) -> float:
    phi1, lambda1 = math.radians(s1_alt), math.radians(s1_az)
    phi2, lambda2 = math.radians(s2_alt), math.radians(s2_az)
    cos_dist = (math.sin(phi1) * math.sin(phi2) + 
                math.cos(phi1) * math.cos(phi2) * math.cos(lambda1 - lambda2))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_dist))))


def perceptual_connection_radius(mag1: float, mag2: float, total_stars: int, base_radius: float = 2.5) -> float:
    """
    Dynamic distance threshold. 
    Scales based on magnitude AND the total density of the sky to mimic human Gestalt perception.
    """
    avg_mag = (mag1 + mag2) / 2.0
    
    # 1. Calculate a Gestalt factor based on how crowded the sky is.
    # We use log10 so the effect curves gracefully. 
    # log10(400 stars) is ~2.6. log10(3000 stars) is ~3.4.
    density_factor = math.log10(max(100, total_stars))
    
    # 2. Calculate a boost. At ~400 stars, the boost is roughly 0. 
    # At 3000+ stars, it adds about 1.2 to 1.5 degrees to the reach.
    gestalt_boost = (density_factor - 2.6) * 1.5
    
    # 3. Apply the boost to both the base radius (for faint clusters) 
    # and the dynamic reach (for bridging bright stars).
    dynamic_base = base_radius + gestalt_boost
    dynamic_reach = 8.0 - (avg_mag * 1.1) + gestalt_boost
    
    return max(dynamic_base, dynamic_reach)


def fold_stars(stars: List[StarResult], max_leads: int = 3) -> Tuple[List[StarCluster], List[StarResult]]:
    """
    Groups stars into clusters using a Density-Based Proximity Graph.
    """
    total_stars = len(stars)
    if total_stars == 0:
        return [], []
        
    # 1. Build a Proximity Graph (Edges between perceived neighbors)
    adj = {i:[] for i in range(total_stars)}
    for i in range(total_stars):
        s1 = stars[i]
        for j in range(i + 1, total_stars):
            s2 = stars[j]
            dist = angular_distance(s1.azimuth, s1.altitude, s2.azimuth, s2.altitude)
            
            # Pass total_stars here!
            threshold = perceptual_connection_radius(s1.magnitude, s2.magnitude, total_stars)
            
            if dist <= threshold:
                adj[i].append(j)
                adj[j].append(i)
                
    # 2. Extract Connected Components
    visited = set()
    components =[]
    
    for i in range(len(stars)):
        if i not in visited:
            comp = []
            stack = [i]
            visited.add(i)
            while stack:
                curr = stack.pop()
                comp.append(stars[curr])
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
            components.append(comp)
            
    # 3. Analyze Coordinates & Shapes for each Component
    clusters = []
    lonely =[]
    
    for comp in components:
        # Sort members by brightness so the Leads are always first
        comp.sort(key=lambda s: s.magnitude)
        
        if len(comp) == 1:
            lonely.append(comp[0])
            continue
            
        # A. Calculate exact center using 3D vector mean
        x = y = z = 0.0
        for s in comp:
            alt_r = math.radians(s.altitude)
            az_r = math.radians(s.azimuth)
            x += math.cos(alt_r) * math.cos(az_r)
            y += math.cos(alt_r) * math.sin(az_r)
            z += math.sin(alt_r)
            
        center_az = math.degrees(math.atan2(y, x)) % 360
        center_alt = math.degrees(math.atan2(z, math.hypot(x, y)))
        
        # B. Calculate group span (Width and Height in degrees)
        alts = [s.altitude for s in comp]
        height = max(alts) - min(alts)
        
        # Shift azimuths relative to center to avoid the 360/0 degree wrap-around bug
        shifted_azs =[((s.azimuth - center_az + 180) % 360) - 180 for s in comp]
        width = max(shifted_azs) - min(shifted_azs)
        
        # Package Leads vs Followers
        num_leads = min(max_leads, len(comp))
        
        clusters.append(StarCluster(
            stars=comp,
            leads=comp[:num_leads],
            center_az=center_az,
            center_alt=center_alt,
            width=width,
            height=height
        ))
        
    # Sort clusters by their brightest star
    clusters.sort(key=lambda c: c.leads[0].magnitude)
    lonely.sort(key=lambda s: s.magnitude)
    
    return clusters, lonely