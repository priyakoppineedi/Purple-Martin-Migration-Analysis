import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import LineString
import gradio as gr
from folium.plugins import FastMarkerCluster
import matplotlib.pyplot as plt
from joblib import Memory

# Use caching to store results of expensive computations
memory = Memory(location="cache_dir", verbose=0)

# Load the datasets
birds_df = pd.read_csv(r"purple_martin.csv")
world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
protected_filepath = r"SAPA_Aug2019-shapefile-polygons.shp"
protected_areas = gpd.read_file(protected_filepath)
    
# Convert birds dataframe into a GeoDataFrame
@memory.cache
def convert_to_geodf(birds_df):
    birds = gpd.GeoDataFrame(birds_df, geometry=gpd.points_from_xy(birds_df['location-long'], birds_df['location-lat']))
    birds.crs = 'EPSG:4326'
    return birds

birds = convert_to_geodf(birds_df)

def load_data():
    return birds_df.head()
    
def CIGDF():
    return birds.head()
# Filter the world dataset for Americas
americas = world.loc[world['continent'].isin(['North America', 'South America'])]
south_america = world.loc[world['continent'] == 'South America']

# Precompute paths, start, and end locations
@memory.cache
def precompute_paths(birds):
    path_df = birds.groupby("tag-local-identifier")['geometry'].apply(list).apply(lambda x: LineString(x)).reset_index()
    path_gdf = gpd.GeoDataFrame(path_df, geometry=path_df.geometry)
    path_gdf.crs = 'EPSG:4326'
    
    start_df = birds.groupby("tag-local-identifier")["geometry"].apply(list).apply(lambda x: x[0]).reset_index()
    start_gdf = gpd.GeoDataFrame(start_df, geometry=start_df.geometry)
    start_gdf.crs = 'EPSG:4326'
    
    end_df = birds.groupby("tag-local-identifier")["geometry"].apply(list).apply(lambda x: x[-1]).reset_index()
    end_gdf = gpd.GeoDataFrame(end_df, geometry=end_df.geometry)
    end_gdf.crs = 'EPSG:4326'

    return path_gdf, start_gdf, end_gdf

path_gdf, start_gdf, end_gdf = precompute_paths(birds)

# Simplify protected areas with a higher tolerance for faster rendering
@memory.cache
def simplify_protected_areas(protected_areas):
    return protected_areas.simplify(tolerance=0.1, preserve_topology=True)

protected_areas_simplified = simplify_protected_areas(protected_areas)

### Folium Maps ###

# Function to create a Folium map combining bird locations, paths, and protected areas
def create_combined_map():
    map_center = [10, -60]
    m = folium.Map(location=map_center, zoom_start=3)

    # Plot protected areas
    folium.GeoJson(
        data=protected_areas_simplified.to_json(),
        style_function=lambda x: {'fillColor': 'green', 'color': 'green', 'weight': 1, 'fillOpacity': 0.4}
    ).add_to(m)

    # Add a fast marker cluster for bird locations
    bird_locations = [[point.y, point.x] for point in birds.geometry]
    FastMarkerCluster(bird_locations).add_to(m)

    # Plot migration paths
    num_paths = len(path_gdf)
    colors = plt.cm.get_cmap('tab20', num_paths).colors
    for idx, row in path_gdf.iterrows():
        color = f"#{int(colors[idx][0]*255):02x}{int(colors[idx][1]*255):02x}{int(colors[idx][2]*255):02x}"
        folium.PolyLine(locations=[(coord[1], coord[0]) for coord in row.geometry.coords], color=color, weight=2.5, opacity=1).add_to(m)

    return m._repr_html_()

### Matplotlib Static Maps ###

# Function to plot bird locations on Americas (Matplotlib)
def plot_americas_with_birds():
    fig, ax = plt.subplots(figsize=(10, 10))
    americas.plot(ax=ax, color="blue", linestyle=":", edgecolor="black")
    birds.plot(ax=ax, color="red", markersize=10)
    plt.title("Bird Locations on Americas")
    return fig

# Function to plot migration paths using Matplotlib
def plot_migration_paths():
    fig, ax = plt.subplots(figsize=(10, 10))
    americas.plot(ax=ax, color="pink", linestyle=":", edgecolor="black")
    start_gdf.plot(markersize=30, color="brown", ax=ax, label="Start Locations")
    end_gdf.plot(markersize=30, color="red", ax=ax, label="End Locations")
    path_gdf.plot(color="green", ax=ax, label="Migration Paths", cmap="tab20b")
    plt.title("Migration Paths of Purple Martins")
    plt.legend()
    return fig

# Function to plot protected areas in South America (Matplotlib)
def plot_protected_areas():
    fig, ax = plt.subplots(figsize=(10, 10))
    south_america.plot(ax=ax, color="white", edgecolor="black")
    protected_areas_simplified.plot(ax=ax, color="green", alpha=0.4)
    plt.title("Protected Areas in South America")
    return fig

### Gradio Interface ###

with gr.Blocks() as demo:

    # Introduction
    gr.Markdown("""
        ## Purple Martin Migration Analysis
        Purple Martins are migratory birds traveling between North and South America. Due to threats like habitat loss and pesticide exposure, their populations are in decline. In this project, we are analyzing their migration patterns by leveraging geographic data to track their movements from North to South America.
        Our goal is to understand their migration routes and assess whether these routes overlap with protected areas. By visualizing their paths and overlaying protected regions, we aim to evaluate the effectiveness of current conservation efforts and ensure that Purple Martins are reaching safe habitats. This analysis will aid in the protection and survival of this vulnerable species""")


    load_button = gr.Button("Load Data")
    with gr.Row():
        gr.Markdown("""
    we begin by importing essential libraries: pandas as pd for data manipulation, 
    geopandas as gpd for handling geospatial data, and shapely.geometry to use LineString for geometric operations. 
    We also import gradio as gr to build interactive web interfaces and matplotlib.pyplot as plt for plotting. 
    The script then loads the dataset "purple_martin.csv" into a pandas DataFrame named birds_df using pd.read_csv(). 
    This DataFrame will store the dataset, which includes recorded location points and information on various Purple Martins, allowing us to perform data analysis and create visualizations.
    """)
        output1 = gr.Textbox(label="Data Loaded", placeholder="Dataset not loaded yet.")
    load_button.click(load_data, [], output1)

    con_geospatial = gr.Button("Convert into GeoDataFrame")
    with gr.Row():
        gr.Markdown("""
    we convert the birds_df DataFrame into a GeoDataFrame named birds using GeoPandas.
    The gpd.GeoDataFrame() function is used to create this GeoDataFrame, where the geometry parameter is set by converting the longitude and
    latitude columns ('location-long' and 'location-lat') into geometric points using gpd.points_from_xy(). This transformation allows us to work with spatial data more effectively.
    The crs (Coordinate Reference System) of the GeoDataFrame is then set to "EPSG:4326", which is a commonly used CRS for geographic coordinates based on latitude and longitude.
""")
        output5 = gr.Dataframe(label="converting into geodataFrame")
    con_geospatial.click(CIGDF, [], output5)
    
    # Bird Locations on Americas (Matplotlib)
    plot_button_birds_static = gr.Button("Display Bird Locations on Americas")
    with gr.Row():
        gr.Markdown("""
    The world map data is first loaded into a GeoDataFrame named world using GeoPandas' built-in dataset naturalearth_lowres.
    This dataset contains geographic boundaries and attributes for various countries.
    Next, the data is filtered to include only North and South America, creating a new GeoDataFrame called americas.
    This filtered data is then plotted using the plot() function, with the countries in the Americas displayed in blue with dashed boundaries and black edges.
    Finally, the birds GeoDataFrame, which contains location data for Purple Martins, is overlaid on this map with red points representing bird locations, using a markersize of 10.
""")
        bird_locations_static_output = gr.Plot(plot_americas_with_birds)

    plot_button_birds_static.click(plot_americas_with_birds, [], bird_locations_static_output)

    # Migration Paths (Matplotlib)
    
    plot_button_paths = gr.Button("Display Migration Paths (Matplotlib)")
    
    with gr.Row():
        gr.Markdown("""
  
    This approach visualizes Purple Martin migration paths by creating path_df,
    which aggregates bird location points into LineString objects representing migration routes.
    This data is then converted into the path_gdf GeoDataFrame.
    It also captures the starting and ending points of each bird's migration in start_df and end_df,
    converting them to start_gdf and end_gdf. The resulting map of the Americas is displayed with pink for the continents,
    brown markers for starting points, red markers for ending points, and green lines for migration paths, showcasing the birds'
    routes across the continents.    """)
        migration_paths_output = gr.Plot(plot_migration_paths)

    plot_button_paths.click(plot_migration_paths, [], migration_paths_output)
    
    # Protected Areas in South America (Matplotlib)
    plot_button_protected = gr.Button("Display Protected Areas Map")
    with gr.Row():
        gr.Markdown("""
    
    The shapefile containing protected areas is loaded into a GeoDataFrame named protected_areas using GeoPandas.
    The data from americas is then filtered to include only South America, creating a new GeoDataFrame called south_america.
    This filtered map is plotted with a white background and black edges. On top of this map, the protected areas are overlaid in
    green with a transparency level of 0.4, highlighting regions designated for conservation within South America.
    """)
        protected_areas_output = gr.Plot(plot_protected_areas)
    plot_button_protected.click(plot_protected_areas, [], protected_areas_output)

    
    # Bird Locations Map (Folium)
    gr.Markdown("""
        ## Purple Martin Migration: Bird Locations, Migration Paths, and Protected Areas
        
        This map shows the migration paths of Purple Martins, their locations, and overlays protected areas in South America.
    """)
    bird_locations_output = gr.HTML(create_combined_map)
    plot_button_birds = gr.Button("Display Bird Locations Map")
    plot_button_birds.click(create_combined_map, [], bird_locations_output)

    # Conclusion
    gr.Markdown("""
        ## Conclusion
        We started by plotting the migration patterns of the birds, tracking their movement across different seasons.
        This analysis revealed which protected areas the birds are likely to visit. We observed various insights from each plot, emphasizing the importance of these protected regions.
        Given the endangered status of these species, we closely examined the locations they frequently visit to ensure they have access to safe habitats,
        such as forests and lakes. In the final plot, we compared the birds' GeoDataFrame with the protected areas' GeoDataFrame.
        This visualization is crucial for implementing special regulations to protect these species from further endangerment.    """)

demo.launch()
