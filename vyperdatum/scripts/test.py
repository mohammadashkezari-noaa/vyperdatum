from pyproj import Transformer

# Define source and target CRS
src_crs = "EPSG:26910"   # NAD83 / UTM zone 15N
src_crs = "EPSG:3740"   # NAD83(HARN) / UTM zone 15N
dst_crs = "EPSG:6339"   # NAD83(2011) / UTM zone 15N

# Create transformer
transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

# Input points (x, y)
points = [
    [546252.0000000009, 5025087.000000002],
    [573641.0000000009, 5046630.000000002]
]

# Transform points
transformed_points = [transformer.transform(x, y) for x, y in points]

# Print results
for i, (src, dst) in enumerate(zip(points, transformed_points), start=1):
    print(f"Point {i} from {src} -> {dst}")
