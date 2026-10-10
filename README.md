# WaveLink

Bu uygulama bilgisayarınızdaki Spotify'dan açılan müziği telefonunuzdan kontrol etmenize yarar



**Not :** Bu proje yalnızca Windows'da dügzün çalışır. Farklı işletim sistemlerinde hata alma ihtimaliniz vardır.

**Not :** Aşağıdaki kurulum ve çalıştırma adımları Windows 10 veya 11'e aittir.

# Kurulum
Gerekenler :
  - Windows 10/11
  - Python 3.10+
  - Spotify Developer App Credentials

```batch
python install -r reqs.txt
```

Kütüphaneler indikten sonra ;
- [https://developer.spotify.com/dashboard] (Spotify Developer Dashboard) sitesinden bir uygulama oluşturun.
- Oluşturduğunuz uygulamanın Redirect URI'sine `http://localhost:8888/callback` yazın.
- Uygulamanın `Client ID` ve `Client Secret` verilerini `config.json` dosyasına girin.


# Çalıştırma
```batch
python main.py
```


# Kullanım
Bilgisayardan server'ı başlattıkdan sonra telefonunuzdan `http://{PC_IP}:5000` adresini açın
Telefonu yatay moda soktuktan sonra kullanmaya başlayabilirsiniz.
