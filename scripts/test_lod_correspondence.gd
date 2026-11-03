# SPDX-License-Identifier: GPL-3.0-or-later
# Godot --headless --script /absolute/path/to/this/script
extends SceneTree
const Review = preload("review_skin_lod_godot.gd")

func _initialize():
    var tolerance = 1e-5
    var rng = RandomNumberGenerator.new()
    rng.seed = 12345
    var points = [Vector3.ZERO, Vector3.ZERO, Vector3(-tolerance, 0, 0), Vector3(tolerance, 0, 0)]
    for index in range(300):
        points.append(Vector3(rng.randf_range(-2, 2), rng.randf_range(-2, 2), rng.randf_range(-2, 2)))
    var grid = Review.correspondence_grid(points, tolerance)
    var queries = [Vector3.ZERO, Vector3(tolerance / 2, 0, 0), Vector3(-tolerance / 2, 0, 0), Vector3(10, 10, 10)]
    for point in points:
        queries.append(point)
        queries.append(point + Vector3(.6, -.5, .3) * tolerance)
        queries.append(point + Vector3(2, 2, 2) * tolerance)
    for query in queries:
        var nearest = INF
        var expected = -1
        for index in range(points.size()):
            var distance = query.distance_to(points[index])
            if distance < nearest:
                nearest = distance
                expected = index
        var actual = Review.nearest_correspondence(query, points, grid, tolerance)
        if actual.index != expected or actual.distance != nearest:
            push_error("Spatial lookup disagrees with exhaustive nearest match")
            quit(1)
            return
    print("Correspondence exhaustive comparison passed: ", queries.size(), " queries")
    quit(0)
