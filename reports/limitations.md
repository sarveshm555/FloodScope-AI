# FloodScope AI — Technical Limitations & Operational Scope

FloodScope AI is an evidence-based prototype developed for the Multimodal AI Hackathon 2026. This document specifies the inherent technical, physical, and observational constraints of spaceborne flood mapping and graph modeling.

---

### 1. Satellite Revisit & Acquisition Constraints
- **Orbit Temporal Gaps:** Sentinel-1 radar satellites operate on deterministic orbital tracks. In a single-satellite operational scenario, exact repeat-pass orbit tracks occur every 12 days. Floods occurring between repeat tracks cannot be observed under identical incidence angles.
- **Monsoon Cloud Penetration vs. Optical Sensor Blindness:** While Sentinel-1 SAR penetrates cloud cover, optical sensors (Sentinel-2) are frequently obscured by heavy monsoon clouds (>70–90% cloud cover during late August in the Himalayas), limiting multi-spectral validation.

### 2. Radar Terrain Effects (Himalayan Topography)
- **Layover, Foreshortening, and Shadow:** In deep mountainous river canyons like the Trishuli Valley, steep slopes facing the radar sensor suffer from foreshortening and layover, while opposing valley walls experience radar shadow. Surface water within radar shadow cannot be detected by backscatter thresholding alone.
- **Surface Water Specular Reflection vs. Calm Pavements:** Calm, flat asphalt surfaces, airport runways, and sandy banks can exhibit low radar backscatter similar to smooth open water, requiring contextual pre-event infrastructure masking and elevation slope restrictions.

### 3. OpenStreetMap Coverage & Pre-Event Snapshots
- **Pre-Event Rule Compliance:** To prevent post-disaster mapping bias, FloodScope AI strictly queries historical pre-event OSM data dated July 27, 2026.
- **Incomplete Local Tagging:** Rural mountain trails or unclassified rural tracks may be omitted or irregularly tagged in OpenStreetMap. A missing road edge in the graph does not prove that no foot trail exists physically on the ground.

### 4. Road Disruption & Infrastructure Exposure Assumptions
- **Exposure vs. Destruction:** A building or road segment whose bounding geometry intersects a candidate flood polygon is classified as *potentially exposed*, never as *confirmed destroyed*. Structural survivability depends on foundation depth, construction type, and flow velocity.
- **Graph Reachability Assumptions:** Settlements are classified as *disconnected* strictly when the modeled graph components become disconnected. Alternative emergency footpaths or temporary culverts are outside the scope of vector graph reachability.

### 5. Operational Safety Notice
> **DISCLAIMER:** FloodScope AI is designed as a decision-support and educational prototype. It is not an operational life-safety dispatch system. Evacuation commands, bridge closures, and humanitarian relief routing must be corroborated by local emergency authorities and on-the-ground reconnaissance teams.
