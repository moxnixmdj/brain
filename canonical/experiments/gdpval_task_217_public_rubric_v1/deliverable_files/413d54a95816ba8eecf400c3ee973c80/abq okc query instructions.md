# I-40 Albuquerque-to-Oklahoma City Overpass export

The companion file `abq okc query.overpassql` selects I-40 motorway and motorway-link ways inside a bounding box covering the Albuquerque, New Mexico to Oklahoma City, Oklahoma corridor. It outputs the selected way tags first, then their member nodes with coordinates.

## Run with Overpass Turbo

1. Open Overpass Turbo in a browser.
2. Paste the complete contents of `abq okc query.overpassql` into the query editor.
3. Choose **Run**. The query uses JSON output and a 180-second timeout.
4. When it completes, choose **Export** and save the raw response as JSON. The JSON is machine-readable OSM data containing way metadata plus node coordinates.

## Run from the command line

From the directory containing the query file:

```bash
curl --fail --show-error --location \
  --data-urlencode "data@abq okc query.overpassql" \
  https://overpass-api.de/api/interpreter \
  --output i40_abq_okc.json
```

The resulting `i40_abq_okc.json` can be retained as Overpass JSON or converted to another machine-readable geospatial format such as GeoJSON with an OSM-aware conversion tool.

## Use for speed and lane analysis

For each returned I-40 way, inspect tags such as `maxspeed`, `maxspeed:forward`, `maxspeed:backward`, `lanes`, `lanes:forward`, and `lanes:backward`. Join each way to its returned member-node coordinates to reconstruct roadway geometry. Treat absent speed or lane tags as missing data rather than inventing values, and preserve the original OSM tags for provenance.
