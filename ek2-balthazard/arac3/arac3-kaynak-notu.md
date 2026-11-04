# Araç 3 kaynak ve kapsam notu

## İncelenen kaynaklar

- Yeni Metin Belgesi (2).txt: Araç 3 için verilen 16 branşın başlık ve alt kayıtlarının kaynak listesi.
- 20210928-4-1.pdf: 28.09.2021 tarihli Resmî Gazete Ek-1 Hastalık Listesi. PDF taranmış görüntü olduğundan metin çıkarımı yerine sayfa görüntüleriyle kontrol edilmiştir.
- FAS ekran görüntüleri: FAS 0–5 açıklamaları ve düzey eşlemesi için arayüz kaynağı.

## Veri üretim kuralı

TXT’deki 16 branş başlığı ve her başlığın altındaki tüm normal kayıtlar Araç 3’e aktarılmıştır. Boş satırlar ve yalnızca işaret görevi gören FAS / hesaplayıcı satırları ayrı hastalık olarak üretilmemiştir. Bu işlem sonucunda 182 kayıt vardır:

- 16 branş
- 182 kaynak kaydı
- 18 hasFas: true kaydı
- 1 calculator: KDS kaydı (Kognitif bozukluklar)

Her kayıtta TXT dosya adı, satır numarası, PDF bölüm adı ve görsel olarak doğrulanan basılı PDF sayfa aralığı source alanında tutulur. Klinik kriter metni veri içine yeniden yazılmamış; kaynakta olmayan kriter veya hastalık üretilmemiştir.

## Önceki 17 sabit kaydın durumu

Önceki arayüz prototipindeki 17 kayıt tam liste değildi. Bunlar yalnızca arama ve seçim akışını göstermek için seçilmiş örneklerdi. 182 kayıtlık kaynak aktarımında:

- Kaynakta bulunan 17 kayıt korunmuş ve kaynak bölümüne bağlanmıştır.
- Kaynakta bulunup prototipte olmayan kayıtlar eklenmiştir.
- Prototipteki Amputasyonlar – alt ekstremite ifadesi, TXT’deki üst başlık ve alt düzey kayıtlarıyla ayrıştırılmıştır.
- Kognitif bozukluklar altındaki hesaplayıcı işareti calculator: KDS olarak bağlanmıştır.
- FAS satırları bağımsız hastalık yapılmamış, TXT’deki kendisinden önce gelen kayda hasFas: true olarak korunmuştur.
- Prototipte kaynak karşılığı bulunmayan klinik kriter, oran veya düzey eklenmemiştir.

Araç 3 bilgi ve yönlendirme ekranıdır; Balthazard hesabı yapmaz ve sağlık kurulu yerine klinik düzey kararı vermez.
