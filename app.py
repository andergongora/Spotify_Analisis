#streamlit run app.py

# Gráfico acumulado de escuchas de una canción


import json
import os
import zipfile
import pandas as pd
import shutil
import matplotlib.pyplot as plt
import streamlit as st

from datetime import timedelta

# Título de la aplicación
st.title("Análisis de Música en Spotify")

st.write("""
Si bien Spotify Wrapped se conoce comúnmente como una recopilación anual de datos, solo se cuenta la actividad del 1 de enero al 31 de octubre para un año determinado.

A diferencia del Wrapped, aquí se tiene en cuenta TODOS los días del año, desde el 1 de enero hasta el 31 de diciembre.

Para que cuente la canción, se ha tenido que escuchar más de 10 segundos.

Para hacer el ranking de canciones más escuchadas, se puede tener en cuenta cuánto tiempo se ha escuchado cada canción o las veces que se ha escuchado cada canción.
         """)

@st.cache_data(show_spinner=False)
def load_data(uploaded_zip):
    # Crear un directorio temporal para extraer el contenido
    dir = os.getcwd()
    path = os.path.join(dir, 'data')
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    
    # Extrae el archivo ZIP
    with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
        zip_ref.extractall(path=path)

    # Mover los archivos extraídos si están en subdirectorios
    subdirs = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    for subdir in subdirs:
        for file in os.listdir(os.path.join(path, subdir)):
            os.rename(os.path.join(path, subdir, file), os.path.join(path, file))
        os.rmdir(os.path.join(path, subdir))

    # Procesa los archivos JSON extraídos
    data = []
    for file in os.listdir(path):
        if file.endswith('.json'):
            with open(os.path.join(path, file), 'r', encoding="utf8") as f:
                data.append(pd.DataFrame(json.load(f)))
                
    # Combina todos los datos en un solo DataFrame
    data = pd.concat(data, ignore_index=True)
    data['ts'] = pd.to_datetime(data['ts'], utc=True)
    data["year"] = data["ts"].dt.year
    data = data[data['ms_played'] > 1000 * 10]
    data = data.sort_values(by='ts')
    return data

# Carga del archivo ZIP
uploaded_zip = st.file_uploader("Carga un archivo ZIP con los datos de Spotify", type="zip")

# Procesa el archivo ZIP si se ha cargado
if uploaded_zip is not None:
    with st.spinner('Cargando datos...'):
        data = load_data(uploaded_zip)


    # Canciones
    songs = data[data["episode_name"].isnull()].copy()


    total_canciones = songs.groupby(["master_metadata_track_name", "master_metadata_album_artist_name"]).size().sort_values(ascending=False)
    total_minutos = songs["ms_played"].sum() / 1000 / 60


    st.write("## Estadísticas de Spotify")

    # Mostrar información general
    st.write(f"Has escuchado un total de **{len(total_canciones)}** canciones diferentes y **{int(total_minutos)}** minutos en Spotify, ¡WOOOW!")

    # Mostrar el gráfico de minutos por año
    spotify_green = "#1DB954"
    spotify_gray = "#B3B3B3"

    fig, ax = plt.subplots()
    yearly_minutes = songs.groupby('year')["ms_played"].sum().apply(lambda x: x / 1000 / 60)
    years = yearly_minutes.index
    minutes = yearly_minutes.values

    ax.plot(years, minutes, marker='o', color=spotify_green, linewidth=2)
    ax.set_title('Número de minutos escuchados en Spotify', color=spotify_green, fontsize=16, fontweight="bold", pad=20)
    ax.set_xlabel('Año', fontsize=12, fontweight="bold")
    ax.set_ylabel('Minutos', fontsize=12, fontweight="bold")
    ax.ticklabel_format(style='plain', axis='y')
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(spotify_gray)
    ax.spines["bottom"].set_color(spotify_gray)
    ax.xaxis.label.set_color(spotify_gray)
    ax.yaxis.label.set_color(spotify_gray)
    ax.tick_params(colors=spotify_gray)

    for year, minute in zip(years, minutes):
        ax.text(year, minute+2000, f'{minute:.0f}', color=spotify_gray, ha='center', va='bottom', fontsize=10, fontweight="bold")

    st.pyplot(fig)

    # Top 25 canciones
    st.write("### Top 25 Canciones Más Escuchadas")
    criterio = st.selectbox("Ordenar por:", ["Minutos Escuchados", "Veces Escuchada"])
    # Obtener las fechas de inicio y fin del dataset
    start_date = songs.ts.min().date()
    end_date = songs.ts.max().date()

    # Selección de rangos de tiempo predefinidos
    st.write("### Filtrar por rango de tiempo")
    # Crear columnas para colocar el selector de rango de tiempo y el selector de fechas en la misma fila
    col1, col2 = st.columns([2, 3])  # Ajusta el ancho de las columnas si es necesario

    with col2:
        # Selección de rangos de tiempo predefinidos
        filter_option = st.radio(
            "Filtrar por:",
            ("Últimos 3 meses", "Último medio año", "Último año", "Total"),
            index=3,  # Por defecto selecciona "total"
            horizontal=True  # Pone los botones en línea horizontal en la misma columna
        )

        # Ajustar las fechas según el rango seleccionado
        end_date = songs.ts.max().date()
        if filter_option == "Últimos 3 meses":
            start_date = end_date - timedelta(days=90)
        elif filter_option == "Último medio año":
            start_date = end_date - timedelta(days=180)
        elif filter_option == "Último año":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = songs.ts.min().date()  # "total" muestra el rango completo

    with col1:
        # Slider para rango de fechas personalizado
        date_range = st.date_input(
            "Rango de fechas:",
            value=(start_date, end_date),  # Rango de fechas inicial basado en el filtro
            min_value=songs.ts.min().date(),
            max_value=songs.ts.max().date(),
        )

    # Verificar si el usuario ha seleccionado ambas fechas en el slider
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        st.write("Por favor, selecciona un rango de fechas completo.")

    # Filtrar las canciones según el rango de fechas seleccionado
    filtered_songs = songs[(songs.ts.dt.date >= start_date) & (songs.ts.dt.date <= end_date)]



    # Top 50 canciones de toda la vida

    # Minutos escuchados las 50 canciones más escuchadas
    top_songs1 = filtered_songs.groupby(["master_metadata_track_name", "master_metadata_album_artist_name"])["ms_played"].sum().apply(lambda x: int(x / 1000 / 60)).sort_values(ascending=False)
    top_songs1 = top_songs1.reset_index()
    top_songs1.columns = ["Canción", "Artista", "Minutos Escuchados"]

    top_songs1.head()
    unique_songs = filtered_songs[["master_metadata_track_name", "master_metadata_album_artist_name", "spotify_track_uri"]].drop_duplicates(
        subset=["master_metadata_track_name", "master_metadata_album_artist_name"]
    )
    top_songs1 = top_songs1.merge(unique_songs, left_on=["Canción", "Artista"], right_on=["master_metadata_track_name", "master_metadata_album_artist_name"])

    # Eliminamos las columnas extras de la fusión para simplificar
    top_songs1 = top_songs1.drop(columns=["master_metadata_track_name", "master_metadata_album_artist_name"])

    top_songs2 = filtered_songs.groupby(["master_metadata_track_name", "master_metadata_album_artist_name"]).size().sort_values(ascending=False)
    top_songs2 = top_songs2.reset_index()
    top_songs2.columns = ["Canción", "Artista", "Veces Escuchada"]

    top_songs=pd.merge(top_songs1, top_songs2, on=["Canción", "Artista"], how='inner').sort_values(by='Minutos Escuchados', ascending=False)

    # Artistas más escuchados
    top_artists = filtered_songs.groupby(["master_metadata_album_artist_name"])["ms_played"].sum().apply(lambda x: int(x / 1000 / 60)).sort_values(ascending=False)
    top_artists = top_artists.reset_index()
    top_artists.columns = ["Artista", "Minutos Escuchados"]


    top_songs_sorted = top_songs.sort_values(by=criterio, ascending=False)[["Canción", "Artista", "Minutos Escuchados", "Veces Escuchada"]].head(25)
    st.dataframe(top_songs_sorted, use_container_width=True)

    # Top 10 artistas
    st.write("### Top 20 Artistas Más Escuchados")
    st.dataframe(top_artists.head(20))

else:
    st.write("Por favor, carga un archivo ZIP con tus datos de Spotify.")
    st.write("""
## ¿Qué datos cargar?
        
Para obtener los datos de Spotify, sigue estos pasos:

1. Abre Spotify, ve a la sección de Seguridad y privacidad y abre "Privacidad de la cuenta".
    (https://www.spotify.com/es/account/privacy/)

2. Desplázate hasta la sección "Descarga de tus datos".

3. Configura la página para que se vea como la captura de pantalla a continuación (Desmarca las casillas de "Datos de la cuenta" y marca las de "Historial de reproducción ampliado").
        """)

    st.image("spotify_data.png") # use_container_width=True

    st.write("""
    4. Haz clic en el botón "Solicitar los datos".

    5. Espera a recibir un correo electrónico de Spotify con un enlace para descargar tus datos, puede tardar unos días.
            """)
    
    
