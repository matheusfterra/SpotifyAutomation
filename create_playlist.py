import json
import urllib
import requests
import youtube_dl
import numpy as np
from exceptions import ResponseException
from secrets import client_id,client_secret,api_key_youtube,client_id_youtube,client_secret_youtube
import base64
from datetime import datetime, timedelta

spotify_token=0
spotify_user_id=0
refresh_token=0
data = {}

class CreatePlaylist:
    def __init__(self):
        #Função para registro das musicas marcadas com "Gostei"
        self.all_song_info = {}
        global nome_playlist
        global playlist_id

        #Nome para Playlist que será Criada no Spotify
        nome_playlist="YouTube Liked Videos"

    def logout(self):

        data['credentials'] = []
        data['credentials'].append({
            'spotify_user_id': "",
            'spotify_token': "",
            'time': "",
            'refresh_token': ""
        })
        with open('data.json', 'w') as outfile:
            json.dump(data, outfile)

        data['credentials'] = []
        data['credentials'].append({
            'youtube_token': "",
            'refresh_token': "",
            'time': ""
        })
        with open('data_youtube.json', 'w') as outfile:
            json.dump(data, outfile)
        print("Logout concluído com Sucesso!")

    def get_token_youtube(self):
        #Abre o arquivo de dados do youtube
        with open("data_youtube.json", "r") as f:
            my_credentials = json.load(f)
        #Capta registros temporais para comparação
        last_event=my_credentials['credentials'][0]["time"]
        last_event= datetime.strptime(last_event, '%Y-%m-%d %H:%M:%S')
        time_atual=datetime.now()
        #Captura o refresh token para recuperar novo token
        refresh_token = my_credentials['credentials'][0]["refresh_token"]
        #Se houver passado mais de uma hora
        if (time_atual - last_event) > timedelta(minutes=58) or my_credentials['credentials'][0]["youtube_token"]=="":
            #Se não houver refresh token, há a requisição de um novo refresh token
            if refresh_token == "":
                redirect_uri = "https%3A%2F%2Fmatheusterra.com%2F"
                redirect_uri_without_formatation = "https://matheusterra.com/"
                link = "https://accounts.google.com/o/oauth2/auth?client_id={}&redirect_uri={}&scope=https://www.googleapis.com/auth/youtube&response_type=code&access_type=offline".format(client_id_youtube, redirect_uri)
                print("Clique no link a seguir e faça o login: {}".format(link))
                code_youtube = input("Digite o Código: ")
                #Requisção posto
                query = "https://accounts.google.com/o/oauth2/token"
                response = requests.post(
                    url=query,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "authorization_code",
                        "redirect_uri":redirect_uri_without_formatation,
                        "client_secret":client_secret_youtube,
                        "client_id":client_id_youtube,
                        "code":urllib.parse.unquote(code_youtube)
                    }

                )
                #Resposta de requisição
                response_json = response.json()
                # check for valid response status
                if response.status_code != 200 and response.status_code != 201:
                    raise ResponseException(response.status_code)
                else:
                    #Get novo token
                    youtube_token = response_json["access_token"]

                    last_time = datetime.now()
                    data_em_texto = last_time.strftime('%Y-%m-%d %H:%M:%S')
                    data['credentials'] = []
                    data['credentials'].append({
                        'youtube_token': youtube_token,
                        'time': data_em_texto,
                        'refresh_token': refresh_token
                    })
                    #Atualização do arquivo json
                    with open('data_youtube.json', 'w') as outfile:
                        json.dump(data, outfile)
            #Caso haja um refresh token há a requisição de um novo token
            else:
                query = "https://accounts.google.com/o/oauth2/token"
                response = requests.post(
                    url=query,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "refresh_token",
                        "client_secret": client_secret_youtube,
                        "client_id": client_id_youtube,
                        "refresh_token": refresh_token
                    }
                )
                #Resposta da requisição
                response_json = response.json()
                # check for valid response status
                if response.status_code != 200 and response.status_code != 201:
                    raise ResponseException(response.status_code)
                else:
                    youtube_token = response_json["access_token"]

                    last_time = datetime.now()
                    data_em_texto = last_time.strftime('%Y-%m-%d %H:%M:%S')
                    data['credentials'] = []
                    data['credentials'].append({
                        'youtube_token': youtube_token,
                        'time': data_em_texto,
                        'refresh_token': refresh_token
                    })
                    #Atualização do arquivo json
                    with open('data_youtube.json', 'w') as outfile:
                        json.dump(data, outfile)
        #Caso não haja 1 hora ainda, é possível utilizar o antigo token
        else:
            youtube_token = my_credentials['credentials'][0]["youtube_token"]

        return youtube_token

    def get_liked_videos(self):
        """Grab Our Liked Videos & Create A Dictionary Of Important Song Information"""
        #Requisita o token atualizado para recuperar os likeds videos
        youtube_token=self.get_token_youtube()
        query = "https://www.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails%2Cstatistics&myRating=like&key={}".format(
            api_key_youtube)
        response = requests.get(
            url=query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(youtube_token)
            }
        )
        response_json = response.json()
        if response.status_code != 200 and response.status_code != 201:
            raise ResponseException(response.status_code)
        else:
            # collect each video and get important information
            for item in response_json["items"]:
                video_title = item["snippet"]["title"]
                youtube_url = "https://www.youtube.com/watch?v={}".format(
                    item["id"])

                # use youtube_dl to collect the song name & artist name
                video = youtube_dl.YoutubeDL({}).extract_info(
                    youtube_url, download=False)
                song_name = video["track"]
                artist = video["artist"]

                if song_name is not None and artist is not None:
                    # save all important info and skip any missing song and artist
                    self.all_song_info[video_title] = {
                        "youtube_url": youtube_url,
                        "song_name": song_name,
                        "artist": artist,

                        # add the uri, easy to get song to put into playlist
                        "spotify_uri": self.get_spotify_uri(song_name, artist)

                        }

    def verify_playlist(self):
        # Verifica se ja há uma playlist criada
        global spotify_token
        global spotify_user_id
        #Variáveis locais para Função
        exist=False
        id=0
        query = "https://api.spotify.com/v1/users/{}/playlists".format(
            spotify_user_id)
        response = requests.get(
            url=query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        # check for valid response status
        if response.status_code != 200 and response.status_code != 201:
            raise ResponseException(response.status_code)
        else:
            #Caso a solicitação seja concluída com Êxito
            #Retorna a quantidade de playlists do usuario
            quantidade=response_json['total']
            #Retorna nome das playlists do usuario
            names=np.zeros((2,quantidade), dtype='<U25')
            for x in range(0,quantidade):
                names[0][x]=response_json['items'][x]['name']
                names[1][x] = response_json['items'][x]['id']
            #Verifica se há alguma playlist com o mesmo nome da qual será criada
            for x in range(0,quantidade):
                if names[0][x]==nome_playlist:
                    exist=True
                    id=names[1][x]
            #Retorna se já existe ou não, e o ID da playlist
            return exist,id

    def verify_playlist_track(self,playlist_id):
        # Verifica se já existe a música a qual será acrescentada na playlist
        global spotify_token
        global spotify_user_id
        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id)
        response = requests.get(
            url=query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()

        # check for valid response status
        if response.status_code != 200 and response.status_code != 201:
            raise ResponseException(response.status_code)
        else:
            #Quantidade de músicas na playlist
            quantidade = response_json["total"]
            #Criação do vetor para armazenar as URI's das Músicas
            uri_tracks=np.zeros((1,quantidade),dtype='<U75')
            for x in range(0,quantidade):
                uri_tracks[0][x]=response_json["items"][x]["track"]["uri"]
            #Retorno das URI's
            return uri_tracks

    def create_playlist(self):
        global spotify_token
        global spotify_user_id
        #Retorna se a playlist já existe, e qual o ID
        exist,id=self.verify_playlist()
        #Cria uma nova playlist, se não existir
        if exist==False:
            """Create A New Playlist"""
            request_body = json.dumps({
                "name": nome_playlist,
                "description": "All Liked Youtube Videos",
                "public": True
            })

            query = "https://api.spotify.com/v1/users/{}/playlists".format(
                spotify_user_id)
            response = requests.post(
                url= query,
                data=request_body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer {}".format(spotify_token)
                }
            )
            response_json = response.json()

            # playlist id
            print("Sua Playlist {} foi criada com Sucesso!".format(nome_playlist))
            return response_json["id"]
        else:
            return id

    def spotify_authenticate(self):
        with open("data.json", "r") as f:
            my_credentials = json.load(f)
        last_event=my_credentials['credentials'][0]["time"]
        last_event= datetime.strptime(last_event, '%Y-%m-%d %H:%M:%S')
        time_atual=datetime.now()
        refresh_token = my_credentials['credentials'][0]["refresh_token"]

        authorization_concat = client_id + ":" + client_secret
        authorization_bytes = authorization_concat.encode("utf-8")
        authorization_base64 = base64.b64encode(authorization_bytes).decode('utf-8')
        redirect_uri_without_format = "https://matheusterra.com/"
        if (time_atual - last_event) > timedelta(hours=1) or my_credentials['credentials'][0]["spotify_user_id"]=="":
            if refresh_token == "" or my_credentials['credentials'][0]["spotify_user_id"]=="":
                print("Seu último acesso foi a mais de 1 hora. Atualize seu token")

                scope="playlist-modify-public%20user-read-email"
                redirect_uri="https%3A%2F%2Fmatheusterra.com%2F" #URL Encodered by: https://meyerweb.com/eric/tools/dencoder/

                link="https://accounts.spotify.com/authorize?client_id={}&scope={}&response_type=code&redirect_uri={}".format(client_id,scope,redirect_uri)
                print("Clique no link a seguir e faça o login: {}".format(link))
                code_spotify=input("Digite o Código: ")

                query = "https://accounts.spotify.com/api/token"

                response = requests.post(
                    url=query,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization":"Basic {}".format(authorization_base64)
                    },
                    data={
                        "grant_type": "authorization_code",
                        "code": "{}".format(code_spotify),
                        "redirect_uri": "{}".format(redirect_uri_without_format)
                    }

                )
            else:
                query = "https://accounts.spotify.com/api/token"
                response = requests.post(
                    url=query,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": "Basic {}".format(authorization_base64)
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": "{}".format(refresh_token),
                    }

                )
            response_json = response.json()
            # check for valid response status
            if response.status_code != 200 and response.status_code != 201:
                raise ResponseException(response.status_code)
            else:
                if refresh_token == "":
                    refresh_token = response_json["refresh_token"]
                spotify_token = response_json["access_token"]

                query = "https://api.spotify.com/v1/me"
                response = requests.get(
                    url=query,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer {}".format(spotify_token)
                    }
                )
                response_json = response.json()
                # check for valid response status
                if response.status_code != 200 and response.status_code != 201:
                    raise ResponseException(response.status_code)
                else:
                    spotify_user_id =response_json["id"]
                    last_time=datetime.now()
                    data_em_texto = last_time.strftime('%Y-%m-%d %H:%M:%S')
                    data['credentials'] = []
                    data['credentials'].append({
                        'spotify_user_id': spotify_user_id,
                        'spotify_token': spotify_token,
                        'time': data_em_texto,
                        'refresh_token':refresh_token
                    })

                    with open('data.json', 'w') as outfile:
                        json.dump(data, outfile)
        else:
            spotify_token = my_credentials['credentials'][0]["spotify_token"]
            spotify_user_id = my_credentials['credentials'][0]["spotify_user_id"]

        return spotify_token, spotify_user_id

    def get_spotify_uri(self, song_name, artist):
        """Search For the Song"""
        global spotify_token
        global spotify_user_id
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]

        # only use the first song
        uri = songs[0]["uri"]

        return uri

    def add_song_to_playlist(self):
        """Add all liked songs into a new Spotify playlist"""
        print("Verificando Liked Videos")
        global spotify_token
        global spotify_user_id
        global data

        spotify_token,spotify_user_id=self.spotify_authenticate()
        delete=False
        # create a new playlist
        playlist_id = self.create_playlist()
        uris_playlist_tracks=self.verify_playlist_track(playlist_id)
        # populate dictionary with our liked songs
        self.get_liked_videos()

        # collect all of uri
        uris = [info["spotify_uri"]
                for song, info in self.all_song_info.items()]
        quantidade1=len(uris)
        quantidade2=len(uris_playlist_tracks[0])
        pos=np.zeros((1,1),dtype='i4')
        n=0
        #Algoritmo para marcar as posições de Musicas repetidas na lista, para excluí-las depois
        if quantidade2>0:
            for x in range(0,quantidade1):
                for y in range(0,quantidade2):
                    if uris[x]==uris_playlist_tracks[0][y]:
                        pos[0][n]=x
                        pos= np.resize(pos, (1, len(pos[0]) + 1))
                        n=n+1
                        delete=True
                        break
        #Deleta as musicas repetidas
        if delete==True:
            pos=np.delete(pos,len(pos[0])-1)
            uris=np.delete(uris,pos)
            #Converte o vetor para lista
            uris=uris.tolist()

        #Verifica se a lista é diferente de vazio
        if uris!=[]:
            # add all songs into new playlist
            request_data = json.dumps(uris)

            query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
                    playlist_id)

            response = requests.post(
                    url=query,
                    data=request_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer {}".format(spotify_token)
                    }
                )

                # check for valid response status
            if response.status_code != 200 and response.status_code !=201:
                raise ResponseException(response.status_code)
            else:
                print("Musicas adicionadas com sucesso à sua playlist {}".format(nome_playlist))
                response_json = response.json()
                return response_json
        #Se lista vazia, não há novas músicas a serem acrescentadas
        else:
            print("Não há músicas novas à serem acrescentadas.")

if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()
