# Wymagania biznesowe
## Cel projektu
Projekt adresuje potrzebę zbudowania pasywnego, skalowalnego źródła przychodów opartego na autonomicznych agentach AI.  

Kluczowy problem: ręczne przeprowadzanie affiliate marketingu, tworzenia, e-booków i sklepu cyfrowego jest czasochłonne i nie skaluje się. 

Cel: $40k-$50k miesięcznie z samego affiliate marketingu, z kolejnymi strumieniami przychodów dokładanymi na wierzch.

Projekt zakłada 3 etapy wdrożenia, z których pierwzszy skupia się na zautomatyzowaniu affiliate marketingu, drugi dodaje e-booki, a trzeci sklep cyfrowy, np. Shopify.

<div style="margin-top: 40px;"></div>

# Wymagania funkcjonalne

## Etap 1: Automatyzacja Affiliate Marketingu
1. **Agent researchu**: przeszukuje sieć i wybiera 10-15 najbardziej opłacalnych programów afiliacyjnych (szuka droższych usług - high-ticket oraz narzędzi abonentowych - SaaS, które płacą co miesiąc) na podstawie najwyższego zarobku za jedno kliknięcie (EPC) i najwyższej prowizji.
2. **Dashboard z rekomendacjami**: prezentuje wyniki agenta researchu, umożliwiając ręczną akceptację (Human in the loop - HITL) wybranych programów afiliacyjnych.
3. **Agent contentu**: dla zatwierdzonych programów agent automatycznie pobiera dostarczone linki afiliacyjne, samodzielnie generuje artykuły na blogi oraz posty na media społecznościowe, a następnie umieszcza w nich linki i sam publikuje z ustalonym harmonogramem.

## Etap 2: E-booki
1. **Agent e-booków**: Analizuje trendujące tematy, pisze pełne e-booki i formatuje je.
2. **Agent integracji sprzedaży i płatności**: Tworzy prosty sklep internetowy do sprzedaży e-booków, zintegrowany z systemem płatności (np. Stripe).

## Etap 3: Sklep cyfrowy - Shopify
1. **Agent przewidywania trendów**: Analizuje dane rynkowe, trendy produktów cyfrowych.
2. **Agent zarządzania sklepem**: Generuje opisy produktów i wystawia je automatycznie na platformie Shopify.

## Human in the Loop (HITL)
System musi zawierać prosty panel lub system powiadomień (Slack/Discord), który umożliwia ręczne zatwierdzanie rekomendacji agenta. Agenci muszą dostarczyć produkt, który jest gotowy do publikacji, ale człowiek musi zweryfikować i zatwierdzić nowe programy, e-booki oraz nowe produkty przed ich publikacją.


<div style="margin-top: 40px;"></div>


# Rozwiązanie i architektura
Architektura będzie oparta na LangChain, Ollama (lokalne modele), Python, Docker Compose z osobnymi kontenerami odpowiadającymi za konkretne funkcje.

- **Orchestrator**: Główny kontener zbudowany na LangChain, który przyjmuje zadania, decyduje który agent powinien je wykonać i pilnuje stanu całego systemu. Wszystko przechodzi przez niego.  
Zanim cokolwiek zostanie opublikowane, orchestrator wysyła powiadomienie z prośbą o zatwierdzenie przez Discrod/Slack. Agenci czekają na decyzję i bez niej nie ruszają dalej.

Tworzenie i publikowanie kontentu odbywa się w trzech niezależnych etapach, które działają równolegle.

- **Etap 1**: Affiliate Marketing ma trzy komponenty: agent researchu (szuka najlepszych programów afiliacyjnych), agent contentu i publikacji (generuje artykuły/posty i publikuje je po akceptacji) oraz panel z rekomendacjami (prezentuje wybrane programy do przeglądu przed rejestracją).
- **Etap 2**: E-booki: agent researchu tematów, agent piszący i formatujący e-booki oraz gotowa integracja landing page i systemu płatności (Stripe do automatycznej sprzedaży i dostawy).
- **Etap 3**: Shopify: agent przewidujący trendy produktów cyfrowych, agent wystawiający produkty oraz bezpośrednia integracja z Shopify API.

Wszystkie trzy etapy działają na wspólnej warstwie infrastukturalnej: Ollama z lokalnymi modelami, PostgreSQL jako główna baza danych, Redis jako kolejka zadań i cache, całość zarządzana przez Docker Compose i hostowana 24/7 na chmurze.

Warstwa infrastruktury komunikuje się z zewnętrznymi API: media społecznościowe, Stripe, Shopify API, sieci afilacyjne i narzędzia do web scrapingu.

Architektura ma kluczowy element: slot na pluginy - każdy nowy strumień przychodów, który chcemy dodać, wdrażany jest jako osobny kontener i podpinany do orchestratora przez wspólny interfejs. Bez potrzeby przebudowywania systemu.

Przepływ akceptacji (HITL) jest globalny i dotyczy każdego etapu: agent proponuje akcję, następnie orchestrator wysyła powiadomienie, człowiek zatwierdza lub odrzuca, a agent wykonuje lub wstrzymuje działanie w zależności od decyzji. Bez zgody człowieka, żadne treści nie są publikowane.