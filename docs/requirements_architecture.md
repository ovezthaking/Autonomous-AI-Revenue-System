[English](#english) · [Polski](#polski)

<a id="english"></a>
# Business Requirements
## Project Goal
The project addresses the need to build a passive, scalable revenue stream based on autonomous AI agents.

Key problem: manual execution of affiliate marketing, e-book creation, and managing a digital store is time-consuming and unscalable.

Goal: $40k-$50k monthly from affiliate marketing alone, with additional revenue streams layered on top.

The project assumes 3 implementation stages, the first focusing on automating affiliate marketing, the second adding e-books, and the third a digital store, e.g., Shopify.

<div style="margin-top: 60px;"></div>

# Functional Requirements

## Stage 1: Affiliate Marketing Automation
1. **Research agent**: searches the web and selects 10-15 most profitable affiliate programs (looks for high-ticket services and subscription-based SaaS tools that pay monthly) based on the highest earnings per click (EPC) and the highest commission.
2. **Recommendations dashboard**: presents the results of the research agent, enabling manual acceptance (Human in the Loop - HITL) of selected affiliate programs.
3. **Content agent**: for approved programs, the agent automatically downloads the provided affiliate links, independently generates blog articles and social media posts, places the links within them, and publishes them automatically according to a set schedule.

## Stage 2: E-books
1. **E-book agent**: Analyzes trending topics, writes full e-books, and formats them.
2. **Sales and payment integration agent**: Creates a simple online store to sell e-books, integrated with a payment system (e.g., Stripe).

## Stage 3: Digital Store - Shopify
1. **Trend prediction agent**: Analyzes market data and digital product trends.
2. **Store management agent**: Generates product descriptions and lists them automatically on the Shopify platform.

## Human in the Loop (HITL)
The system must include a simple dashboard or notification system (Slack/Discord) that allows for manual approval of agent recommendations. Agents must deliver a product ready for publication, but a human must verify and approve new programs, e-books, and new products before they are published.

<div style="margin-top: 60px;"></div>

# Solution and Architecture
The architecture will be based on LangChain, Ollama (local models), Python, and Docker Compose with separate containers responsible for specific functions.

- **Orchestrator**: The main container built on LangChain, which receives tasks, decides which agent should execute them, and monitors the state of the entire system. Everything passes through it.
Before anything is published, the orchestrator sends a notification requesting approval via Discord/Slack. Agents wait for the decision and do not proceed without it.

Content creation and publication take place in three independent stages that run in parallel.

- **Stage 1**: Affiliate Marketing has three components: a research agent (searches for the best affiliate programs), a content and publication agent (generates articles/posts and publishes them after approval), and a recommendations dashboard (presents selected programs for review before registration).
- **Stage 2**: E-books: a topic research agent, an e-book writing and formatting agent, and a ready integration of a landing page and payment system (Stripe for automated sales and delivery).
- **Stage 3**: Shopify: a digital product trend prediction agent, a product listing agent, and direct integration with the Shopify API.

All three stages operate on a common infrastructure layer: Ollama with local models, PostgreSQL as the main database, Redis as a task queue and cache, all managed by Docker Compose and hosted 24/7 in the cloud.

The infrastructure layer communicates with external APIs: social media, Stripe, Shopify API, affiliate networks, and web scraping tools.

The architecture has a key element: a plugin slot - every new revenue stream we want to add is deployed as a separate container and connected to the orchestrator via a common interface. No need to rebuild the system.

The approval flow (HITL) is global and applies to every stage: the agent proposes an action, then the orchestrator sends a notification, a human approves or rejects, and the agent executes or pauses the action depending on the decision. Without human consent, no content is published.

**Planned stack**:
- Python (main programming language)
- LangChain (agent orchestration, memory management, tool building)
- Ollama - local LLM models (e.g., Llama 3 / Mistral) - optionally Claude API for tasks requiring higher quality
- FastAPI - backend and endpoints for the HITL dashboard and Discord/Slack webhooks
- PostgreSQL - Storing affiliate program profiles, history of generated articles, publications, and the working state of agents.
- Alembic - Versioning and executing PostgreSQL schema migrations as data models evolve.
- Redis + Celery - FastAPI delegates tasks to Redis, and Celery executes them in the background, ensuring the system is not blocked while waiting for responses from external APIs or generating content.
- Docker Compose - Each agent and microservice runs in a separate container, facilitating scaling and management.

**Additionally**:
- Frontend - Next.js + Tailwind CSS + shadcn/ui - a simple interface for reviewing recommendations, publication history, manual approvals, monitoring system states, agent activity, and content management.

<div style="margin-top: 60px;"></div>
<hr>
<div style="margin-top: 60px;"></div>

<a id="polski"></a>
# Wymagania biznesowe
## Cel projektu
Projekt adresuje potrzebę zbudowania pasywnego, skalowalnego źródła przychodów opartego na autonomicznych agentach AI.  

Kluczowy problem: ręczne przeprowadzanie affiliate marketingu, tworzenia, e-booków i sklepu cyfrowego jest czasochłonne i nie skaluje się. 

Cel: $40k-$50k miesięcznie z samego affiliate marketingu, z kolejnymi strumieniami przychodów dokładanymi na wierzch.

Projekt zakłada 3 etapy wdrożenia, z których pierwzszy skupia się na zautomatyzowaniu affiliate marketingu, drugi dodaje e-booki, a trzeci sklep cyfrowy, np. Shopify.

<div style="margin-top: 60px;"></div>

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


<div style="margin-top: 60px;"></div>


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


**Planowany stack**:
- Python (główny język programowania)
- LangChain (orkiestracja agentów, zarządzanie ich pamięcią, budowanie narzędzi)
- Ollama - lokalne modele LLM (np. LLama 3 / Mistral) - opcjonalnie Claude API do zadań wymagających większej jakości
- FastAPI - backend i endpointy dla panelu HITL i webhooków Discord/Slack
- PostgreSQL - Zapis profili programów partnerskich, historii wygenerowanych artykułów, publikacji oraz stanu pracy agentów.
- Alembic - Wersjonowanie i wykonywanie migracji schematu PostgreSQL wraz z rozwojem modeli danych.
- Redis + Celery - FastAPI zleca zadanie do Redis, a Celery wykona je w tle, dzięki czemu system nie będzie blokowany podczas oczekiwania na odpowiedzi z zewnętrznych API lub generowania treści.
- Docker Compose - Każdy agent i mikroserwis działa w osobnym kontenerze, co ułatwia skalowanie i zarządzanie.

**Dodatkowo**:
- Frontend - Next.js + Tailwind CSS + shadcn/ui - prosty interfejs do przeglądania rekomendacji, historii publikacji, ręcznego zatwierdzania, monitorowania stanu systemów, pracy agentów i zarządzania treściami.
