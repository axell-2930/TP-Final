#Carga de las librerías necesarias


import streamlit as st
import math
import pandas as pd
import geopandas as gpd
import plotly.express as px
import folium
from folium import Marker
from folium.plugins import MarkerCluster
from folium.plugins import HeatMap
from streamlit_folium import folium_static


#
# Configuración de la página de Streamlit
#
st.set_page_config(layout='wide')

#
# TÍTULO Y DESCRIPCIÓN DE LA APLICACIÓN
#

st.title('Visualización de datos de biodiversidad, de la Infraestructura Mundial de Información en Biodiversidad')
st.markdown('Esta aplicación presenta visualizaciones tabulares, gráficas y geoespaciales de datos de biodiversidad que siguen el estándar [Darwin Core (DwC)](https://dwc.tdwg.org/terms/).')
st.markdown('El usuario debe de seleccionar y subir un archivo csv con el formato de [Infraestructura Mundial de Información en Biodiversidad (GBIF)](https://www.gbif.org/), este requisito es indispensable, ya que sino cumple con dicho formato, la aplicación no funcionará.')

#
# ENTRADAS 
#

# Carga de los datos.
archivo = st.sidebar.file_uploader('Seleccione un archivo CSV que siga el estándar DwC: (GBIF)](https://www.gbif.org/)')

# Procesamiento de datos
if archivo is not None:
    # Carga de registros de presencia en un dataframe
    Registros_datos = pd.read_csv(archivo, delimiter='\t')
    Registros_datos = gpd.GeoDataFrame(Registros_datos, 
                                           geometry=gpd.points_from_xy(Registros_datos.decimalLongitude, 
                                                                       Registros_datos.decimalLatitude),
                                           crs='EPSG:4326')

    # Cargar el archivo geoespacial
    Cantones_CR = gpd.read_file("datos/Cantones_4326.geojson")

    # Limpieza de datos
    # Eliminación de registros con valores nulos en la columna 'species'
    Registros_datos = Registros_datos[Registros_datos['species'].notna()]
    # Cambio del tipo de datos del campo de fecha
    Registros_datos["eventDate"] = pd.to_datetime(Registros_datos["eventDate"])

    # Especificación de filtros
    # Especie
    lista_especies = Registros_datos.species.unique().tolist()
    lista_especies.sort()
    filtro_especie = st.sidebar.selectbox('Seleccione la especie', lista_especies)


    #
    # PROCESAMIENTOS
    #



    # Filtrado
    Registros_datos = Registros_datos[Registros_datos['species'] == filtro_especie]

    # Cálculo de la cantidad de registros
    # "Join" espacial de las capas de cantones y y observación de especies, este del archivo csv que se cargará
    Registros_Cantones = Cantones_CR.sjoin(Registros_datos, how="left", predicate="contains")
    # Conteo de registros de presencia en cada provincia
    Observaciones_sjoin = Registros_Cantones.groupby("CODNUM").agg(cantidad_registros_presencia = ("gbifID","count"))
    Observaciones_sjoin = Observaciones_sjoin.reset_index()



    #
    # SALIDAS 
    #



    # Tabla
    st.header('Tabla con las especies observadas/registradas')
    st.dataframe(Registros_datos[['species', 'eventDate','stateProvince', 'locality', ]].rename(columns = {'species':'Especies', 'stateProvince':'Provincia de la observación', 'locality':'Localidad (puede haber datos vacíos)', 'eventDate':'Fecha'}))


    # Definición de columnas de la parte visual de nuestra aplicación, dividará el contenido en dos columnas
    col1, col2 = st.columns(2)


    with col1:
        # join
        # "Join" para agregar realizar el gráfico de las observaciones por provincias
        Observaciones_sjoin = Observaciones_sjoin.join(Cantones_CR.set_index('CODNUM'), on='CODNUM', rsuffix='_b')
        # Dataframe filtrado para usar en graficación
        Especies_Provincia = Observaciones_sjoin.loc[Observaciones_sjoin['cantidad_registros_presencia'] > 0, 
                                                                ["provincia", "cantidad_registros_presencia"]].sort_values("cantidad_registros_presencia", ascending=True)
        Especies_Provincia = Especies_Provincia.set_index('provincia')  




        # Gráfico de observaciones por provincia
        st.header('Especies observadas/registradas por provincia')

        Grafico_Provincias = px.bar(Especies_Provincia, 
                        labels={'provincia':'Provincias de Costa Rica', 'cantidad_registros_presencia':'Registros de presencia'})    

        Grafico_Provincias.update_layout(barmode='stack', xaxis={'categoryorder': 'total descending'})
        st.plotly_chart(Grafico_Provincias)    
 


    with col2:
        # join
        # "Join" para grafico cantones
        Observaciones_sjoin = Observaciones_sjoin.join(Cantones_CR.set_index('CODNUM'), on='CODNUM', rsuffix='_b')
        # Dataframe filtrado para usar en graficación
        Especies_Provincia = Observaciones_sjoin.loc[Observaciones_sjoin['cantidad_registros_presencia'] > 0, 
                                                                ["NCANTON", "cantidad_registros_presencia"]].sort_values("cantidad_registros_presencia")
        Especies_Provincia = Especies_Provincia.set_index('NCANTON')  




        # Gráfico de observaciones por cantoón
        st.header('Especies observadas/registradas por cantón')

        Grafico_Cantones = px.bar(Especies_Provincia, 
                        labels={'NCANTON':'Cantones de Costa Rica', 'cantidad_registros_presencia': 'Registros de presencia'})    

        Grafico_Cantones.update_layout(barmode='stack', xaxis={'categoryorder': 'total descending'})
        st.plotly_chart(Grafico_Cantones)

    # Cartografía base, incluye dos basemaps, el que coloca por defecto "OpenStreetMaps" y el específicado en la parte inferior; "ESRI World Imagery"
    st.header('Mapa con las especies observadas/registradas')
    m = folium.Map(
    location=[10, -84],
    zoom_start=8,
    control_scale=True)
    # ESRI World Imagery base map
    folium.TileLayer(
    tiles='http://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/MapServer/tile/{z}/{y}/{x}',
    name='ESRI World Imagery',attr='ESRI World Imagery').add_to(m)





        # Cartografía que incluye la cantidad de casos por cantón
    folium.Choropleth(
        name="Cantones",
        geo_data=Cantones_CR,
        data=Observaciones_sjoin,
        columns=['CODNUM', 'cantidad_registros_presencia'],
        bins=8,
        key_on='feature.properties.CODNUM',
        fill_color='PuBuGn', 
        fill_opacity=0.5, 
        line_opacity=1,
        legend_name='Registro cantón',
        smooth_factor=0).add_to(m)



        # Cartografía que incluye la cantidad de casos por provincia
    folium.Choropleth(
        name="Provincias",
        geo_data=Cantones_CR,
        data=Observaciones_sjoin,
        columns=['provincia', 'cantidad_registros_presencia'],
        bins=8,
        key_on='feature.properties.provincia',
        fill_color='PuBuGn', 
        fill_opacity=0.5, 
        line_opacity=1,
        legend_name='Registros provincia',
        smooth_factor=0).add_to(m)



    # Capa de las observaciones de especies agrupados en puntos
    mc = MarkerCluster(name='Registros agrupados en marcas en observaciones/registros')
    for idx, row in Registros_datos.iterrows():
        if not math.isnan(row['decimalLongitude']) and not math.isnan(row['decimalLatitude']):
            mc.add_child(
                Marker([row['decimalLatitude'], row['decimalLongitude'], ], 
                                popup= str(row["eventDate"]) + str(row["species"]) + str(row["stateProvince"])))




    #Se agregan todas las capas anteriores al mapa

    m.add_child(mc)
    # Control de capas
    folium.LayerControl().add_to(m) 
    # Despliegue del mapa
    folium_static(m, width=1000, height=750)

