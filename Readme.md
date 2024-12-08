Prosty przykład serwera http, który służy to przechwytywania zapytań HTTP metodą POST i typem multipart/form-data.
Własnoręcznie przechwytywanie takiego zapytania umożliwia operowanie na strumieniu danych w trakcie przesyłania.
W tym przykładzie przesyłamy obrazy. Ilość przesyłanych plików jak i ich wielkość może być dowolna.
W trakcie przesyłania wszystkich plików (a nie po jego zakończeniu), każdy plik jest wyłapywany osobno z zapytania i w osobnym wątku zmieniana jest jego rozdzielczość.

W ramach testów można uruchomić serwer http dla pliku index.html komendą:
busybox httpd -p 0.0.0.0:8080

Serwer uruchomi się w tle. Można go zatrzymać komendą:
pkill busybox

Uruchomienie programu:
python main.py

W wywołaniu klasy możemy włączyć/wyłaczyć obługę wątków oraz informacje z debugu
