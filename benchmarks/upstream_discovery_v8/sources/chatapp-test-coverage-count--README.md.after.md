 > [!WARNING]
> **Este proyecto se encuentra actualmente en desarrollo.** Algunas funcionalidades pueden estar incompletas o sujetas a cambios.

<div align="center">

# 💬 ChatApp

**Aplicación de mensajería instantánea para Android**

![Kotlin](https://img.shields.io/badge/Kotlin-2.3.21-7F52FF?style=for-the-badge&logo=kotlin&logoColor=white)
![Jetpack Compose](https://img.shields.io/badge/Jetpack%20Compose-2026.06.01-4285F4?style=for-the-badge&logo=jetpackcompose&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3.6.0-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-FCM-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![LiveKit](https://img.shields.io/badge/LiveKit-2.26.1-E5363B?style=for-the-badge&logo=webrtc&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/AJRPachon/ChatApp/ci.yml?style=for-the-badge&label=CI&logo=githubactions&logoColor=white)

</div>

---

Proyecto personal para poner en práctica lo aprendido en desarrollo Android nativo. El 80% del código y las decisiones de arquitectura son de mi autoría; usé IA (Claude) como guía puntual para cosas concretas: testing, algunas integraciones, la configuración de Gitflow, el pipeline de CI y este mismo README son buenos ejemplos de ello.

---

## ✨ Funcionalidades

### 🔐 Autenticación y cuenta

| | Funcionalidad |
|---|---|
| 📧 | Registro e inicio de sesión con **email/contraseña** y **Google Sign-In** |
| 🔑 | **Autenticación de dos factores** (TOTP) — actívala desde el perfil |
| 🔒 | **Bloqueo de app** — autenticación biométrica tras 30 s en segundo plano |
| 🖥️ | **Auditoría de sesiones** — consulta dispositivos activos y cierra sesiones remotamente |
| 🖼️ | Perfil de usuario con **avatar** e información editable |
| ☁️ | **Copia de seguridad en Drive** — exporta e importa el historial a Google Drive |

### 💬 Mensajería

| | Funcionalidad |
|---|---|
| 💬 | Chat individual y grupal con **texto, imágenes, audio, GIFs y stickers** |
| 🎙️ | **Grabación de audio con forma de onda en vivo** — la barra de grabación muestra la amplitud real mientras hablas, y la vista previa posterior reproduce esa misma forma de onda (no una aleatoria) |
| 🎬 | **Mensajes de vídeo** — graba y envía clips directamente desde la cámara |
| 📍 | **Compartir ubicación** — envía tu posición con enlace a Google Maps |
| 📎 | **Adjuntos agrupados** — botón `+` con galería, cámara, archivo, vídeo y sticker; micrófono separado |
| ↩️ | **Reenvío de mensajes** a otra conversación |
| ✏️ | **Edición y borrado** de mensajes propios |
| ☑️ | **Selección múltiple** de mensajes para borrarlos en lote |
| 💣 | **Mensajes efímeros** con autodestrucción configurable y cuenta atrás visible |
| ⏱️ | **Modo de mensajes temporales** — todos los mensajes de una conversación se autodestruyen tras el tiempo elegido |
| ⏰ | **Mensajes programados** — redacta un mensaje y elige cuándo se enviará automáticamente |
| 📝 | **Borradores** — el texto sin enviar se guarda al salir y se restaura al volver |
| 📌 | **Mensajes fijados** con banner y acceso directo al mensaje |
| 🔖 | **Mensajes guardados** — marca mensajes como favoritos y accede desde tu perfil |
| 😀 | **Reacciones con emoji** — pulsación larga para reaccionar; agrupadas bajo cada burbuja con hoja de detalle de quién reaccionó |
| 🌐 | **Traducción de mensajes** — traduce al español con un toque (ML Kit, sin internet) |
| 🎙️ | **Transcripción de audios** — convierte un mensaje de voz en texto |
| 🔍 | **Búsqueda de mensajes** dentro de una conversación con resaltado del resultado |
| 🔎 | **Búsqueda global** — busca texto en todas las conversaciones desde la pantalla principal |
| 📊 | **Encuestas** — crea encuestas de opción múltiple directamente en el chat |
| 📌 | **Banner de mensaje fijado** — acceso rápido al mensaje fijado activo desde el chat |
| 🖼️ | **Galería de medios del chat** — navega imágenes y vídeos de una conversación en cuadrícula |
| 📇 | **Compartir contactos** — envía una tarjeta de contacto desde la agenda del dispositivo |
| 🎨 | **Fondo de pantalla del chat** — elige un color de fondo diferente por conversación |
| 🔗 | **Vista previa de enlaces** — previsualización automática de URLs en los mensajes |
| 📅 | **Eventos de chat** — crea eventos con fecha, hora y RSVP dentro de una conversación |
| 📄 | **Visor de PDF** — visualiza archivos PDF adjuntos con zoom y navegación |

### 👥 Grupos

| | Funcionalidad |
|---|---|
| 👥 | Gestión completa de grupos: **crear, editar, añadir y expulsar miembros** |
| 🛡️ | **Roles en grupos** — el administrador puede promover o degradar a otros miembros |
| 📣 | **Menciones** (`@nombre`) — autocompletado al escribir `@` con lista de miembros y resaltado en la burbuja |
| 📊 | **Encuestas en grupos** — crea y vota encuestas con múltiples opciones |
| ✅ | **Confirmaciones de lectura en grupos** — lista de quién ha visto cada mensaje con timestamp |
| 📢 | **Listas de difusión** — envía un mensaje a múltiples contactos a la vez sin crear un grupo |

### 📞 Llamadas

| | Funcionalidad |
|---|---|
| 📞 | **Llamadas de voz y videollamadas** individuales |
| 📹 | **Videollamadas grupales** — hasta 8 participantes, vista en cuadrícula y controles de cámara/micrófono |
| 🎥 | **Cambio de cámara** durante una videollamada |
| 🖥️ | **Compartir pantalla** en videollamadas |
| 💬 | **Chat durante llamadas** — panel de mensajes sin interrumpir la llamada |
| ⏺️ | **Grabación de llamadas** — graba el audio y descarga el archivo al finalizar |
| 🌫️ | **Desenfoque de fondo** en videollamadas |
| 🎭 | **Filtros de cámara** — escala de grises, sepia e inversión durante videollamadas |

### 🔔 Notificaciones

| | Funcionalidad |
|---|---|
| 🔔 | **Notificaciones push** con deep links directos a la conversación |
| ↩️ | **Respuesta desde la notificación** sin abrir la app |
| 🎵 | **Sonidos de notificación personalizados** por conversación (selector integrado en ajustes del chat) |
| 🔇 | **Silenciar conversaciones** con opciones de duración (1h, 8h, 24h, siempre) |

### 🗂️ Organización

| | Funcionalidad |
|---|---|
| ⚡ | Lista de conversaciones **en tiempo real** |
| 📡 | **Banner sin conexión** — avisa visualmente cuando el dispositivo pierde la red |
| 🗄️ | **Archivar conversaciones** con búsqueda y orden por no leídos |
| 📁 | **Carpetas de conversaciones** — organiza chats en carpetas accesibles desde la barra lateral |
| ✅ | **Confirmación de lectura** con doble check y badge de mensajes no leídos |
| ✍️ | **Indicador de escritura** en tiempo real |
| 🟢 | **Estado de presencia** — "En línea" / "última vez" con opción de privacidad |

### 🤝 Contactos y social

| | Funcionalidad |
|---|---|
| 🤝 | Sistema de **invitaciones de amistad** con bloqueo de usuarios |
| 🔗 | **Enlace de invitación a grupo** — genera un link único para unirse al grupo sin que el admin tenga que añadir a cada miembro manualmente |
| 📷 | **Código QR de contacto** — comparte tu perfil o añade contactos escaneando un QR |
| 👥 | **Sugerencias de la agenda** — descubre qué contactos ya usan la app |
| 🖼️ | **Galería de medios compartidos** en el perfil del contacto con zoom |
| 📊 | **Estadísticas de uso** — mensajes enviados, recibidos, medios y palabras por conversación |
| 📤 | **Exportar conversación** — descarga el historial como archivo de texto |

### 🔒 Seguridad y privacidad

| | Funcionalidad |
|---|---|
| 🕵️ | **Modo incógnito** — actívalo por conversación para que los mensajes no se guarden en el dispositivo |
| 🎨 | **Temas de color por conversación** — personaliza el fondo y el color de las burbujas |
| 📦 | **Paquetes de stickers** — navega e instala colecciones desde la tienda |

### 🤖 Inteligencia Artificial

| | Funcionalidad |
|---|---|
| 🤖 | **Asistente IA** — resume la conversación, sugiere una respuesta o lanza consultas libres vía Supabase Edge Function |
| 🚀 | **Perfil de inicio optimizado** — Baseline Profile pre-compila rutas críticas de Compose, Room y Coil para un arranque más rápido |

---

## 🏗️ Arquitectura

El proyecto sigue **Clean Architecture** con tres capas bien definidas y el patrón **MVI** en presentación.

```
com.ajrpachon.chatapp/
│
├── 🟣 domain/                     ← Kotlin puro, sin dependencias Android (KMP-ready)
│   ├── model/                        UserBO, MessageBO, ConversationBO, CallBO,
│   │                                 ScheduledMessage, PollBO, PollOptionBO, PollVoteBO,
│   │                                 ContactBO, ThemePreference, ChatTheme,
│   │                                 MediaUrlValidator, MessageLimits, StickerValidation,
│   │                                 InputValidation — validación pura sin imports Android
│   ├── repository/                   Interfaces (contratos) — incluyendo interfaces de
│   │                                 repositorios locales: DraftRepository, IncognitoRepository,
│   │                                 WallpaperRepository, AiAssistantRepository, PollRepository,
│   │                                 ContactRepository, ScheduledMessageRepository
│   └── usecase/                      Un caso de uso por archivo (24 en total)
│
├── 🔵 data/                       ← Implementa las interfaces del dominio
│   ├── local/
│   │   ├── entity/                   21 entidades Room (DBO): mensajes, conversaciones,
│   │   │                             usuarios, invitaciones, reacciones, estados, encuestas,
│   │   │                             stickers, recibos de lectura, carpetas, difusión,
│   │   │                             eventos de chat, sesiones y mensajes programados
│   │   ├── dao/                      15 DAOs de acceso a la BD
│   │   ├── ChatDatabase.kt           Base de datos Room (versión 34, cifrada con SQLCipher)
│   │   ├── DatabaseBuilder.kt        Migraciones v1 → v34 (33 migraciones explícitas)
│   │   └── DatabaseKeyProvider.kt    Clave AES-256 en Android KeyStore
│   ├── remote/
│   │   ├── dto/                      Data Transfer Objects de Supabase
│   │   └── source/                   Fuentes remotas (Supabase, FCM tokens)
│   ├── repository/                   Coordinan caché local ↔ Supabase remoto
│   ├── mapper/                       Mappers centralizados DBO ↔ BO / DTO → DBO:
│   │                                 ConversationMapper, GroupMapper, UserMapper,
│   │                                 MessageMapper, ReactionMapper, StatusMapper,
│   │                                 ScheduledMessageMapper, InvitationMapper
│   └── session/                      Gestión de sesión de autenticación
│
├── 🟢 ui/                         ← Jetpack Compose + MVI
│   ├── common/                       BaseViewModel (State/Intent/Effect), UiConstants
│   │                                 (ChatConstants, CallPermissions), TimeFormatter,
│   │                                 ChatThemeColors (mapeo ChatTheme → colores Compose)
│   ├── auth/                         Login, registro, MFA challenge e IntegrityBlockedScreen
│   ├── conversations/                Lista de conversaciones con carpetas y difusión
│   ├── chat/                         Chat (StickerPicker, EmojiPicker, GiphyClient, asistente IA,
│   │                                 ChatThemeColors); gallery/ con ChatMediaGalleryViewModel
│   ├── call/                         Llamada en curso + overlay de entrante (filtros, grabación, grid grupal)
│   ├── newchat/                      Buscar usuario / importar contactos / escanear QR
│   ├── group/                        Crear grupo y gestión de miembros
│   ├── invitations/                  Invitaciones de amistad
│   ├── profile/                      Perfil propio (2FA, sesiones, backup, estadísticas, bloqueo)
│   ├── userinfo/                     Perfil de otro usuario con galería de medios compartidos
│   ├── status/                       Estados de presencia estilo stories
│   ├── applock/                      Pantalla de bloqueo biométrico (AppLockViewModel)
│   ├── backup/                       Copia de seguridad en Google Drive
│   ├── broadcast/                    Listas de difusión
│   ├── pdf/                          Visor de PDF con PdfRenderer (PdfViewerViewModel)
│   ├── saved/                        Mensajes guardados
│   ├── usagestats/                   Estadísticas de uso con gráfico de barras
│   ├── search/                       Búsqueda global de mensajes (GlobalSearchScreen + ViewModel)
│   ├── components/                   Avatar, Button, TextField, Shimmer, EmojiPickerBottomSheet, OfflineBanner
│   └── theme/                        Color, Shape, Theme (Material3 pastel)
│
├── 🔴 service/                    ← Servicios en background
│   ├── ChatFirebaseMessagingService.kt
│   ├── FcmTokenManager.kt
│   ├── FcmMessageHandler.kt          MessagingStyle + RemoteInput + grouping
│   ├── NotificationReplyReceiver.kt  Inline reply from notification
│   ├── ActiveChatTracker.kt
│   └── PresenceManager.kt            Estado online/offline vía Supabase Realtime
│
├── worker/                        ← WorkManager workers (ScheduledMessageWorker)
├── di/                            ← Módulos Koin (AppModule, SharedModules)
├── utils/                         ← AppLogger, catchResult, E2EEKeyManager,
│                                     OkHttpProvider, SessionGuard, RootDetector,
│                                     ClipboardProtection, IntegrityChecker,
│                                     TranslationManager, AudioTranscriber,
│                                     ContactSyncManager, BackupManager,
│                                     GiphyKeyManager, LinkPreviewFetcher,
│                                     SecureStorage, UploadLimits, NetworkMonitor
├── MainActivity.kt                ← NavDisplay + todas las rutas (Navigation 3)
└── ChatApplication.kt             ← Inicialización de Koin y Supabase

supabase/
├── functions/
│   ├── send-fcm-notification/     ← Edge Function: envía push via FCM v1
│   ├── livekit-token/             ← Edge Function: genera JWT de LiveKit (secreto nunca en cliente)
│   ├── verify-integrity/          ← Edge Function: valida Play Integrity token
│   ├── ai-assistant/              ← Edge Function: proxy al modelo de IA (Claude via Anthropic API)
│   └── assetlinks/                ← Edge Function: sirve /.well-known/assetlinks.json
└── migrations/                    ← Migraciones SQL del esquema
```

### Patrón MVI por pantalla

```kotlin
val state: StateFlow<FooState>    // estado observable
val effects: Flow<FooEffect>      // efectos de un solo uso (navegación, toasts)
fun onIntent(intent: FooIntent)   // punto de entrada único para interacciones
```

---

## 🔒 Seguridad

La app implementa un modelo de seguridad en capas para proteger los mensajes y los datos del usuario:

- **Cifrado de mensajes (E2EE):** los mensajes 1:1 se cifran con ECDH (P-256) + HKDF + AES-256-GCM en el dispositivo antes de enviarse, de modo que Supabase nunca almacena contenido legible. Las claves derivadas se cachean en memoria para evitar round-trips repetidos a la base de datos.
- **Base de datos local cifrada:** la caché de mensajes en el dispositivo está protegida con SQLCipher AES-256, con la clave custodiada por el Android KeyStore.
- **Transporte seguro:** certificate pinning para Supabase y LiveKit, bloqueo de HTTP en claro, rechazo de CAs de usuario y validación de dominios en todas las URLs de medios.
- **Autenticación robusta:** expiración de sesión por inactividad, revocación global al cerrar sesión y secretos de servidor nunca incluidos en el cliente (tokens LiveKit generados en Edge Function).
- **Integridad del dispositivo:** verificación con Play Integrity API al arrancar y detección de root, bloqueando o advirtiendo al usuario si el entorno no es de confianza.
- **Privacidad en uso:** `FLAG_SECURE` impide capturas de pantalla, el portapapeles se limpia automáticamente a los 60 s y los logs se suprimen en producción.
- **Backend endurecido:** RLS estricto en todas las tablas de Supabase, permisos mínimos por rol, límite de tamaño de mensajes en BD y rate limiting en las Edge Functions.

---

## 🛠️ Tecnologías

### Android / Kotlin

| Tecnología | Versión | Uso |
|---|---|---|
| ![Kotlin](https://img.shields.io/badge/-Kotlin-7F52FF?logo=kotlin&logoColor=white) **Kotlin** | 2.3.21 | Lenguaje principal |
| ![AGP](https://img.shields.io/badge/-AGP-3DDC84?logo=android&logoColor=white) **Android Gradle Plugin** | 9.1.1 | Sistema de build |
| ![Compose](https://img.shields.io/badge/-Jetpack%20Compose-4285F4?logo=jetpackcompose&logoColor=white) **Jetpack Compose BOM** | 2026.06.01 | UI declarativa |
| ![M3](https://img.shields.io/badge/-Material%203-757575?logo=materialdesign&logoColor=white) **Material 3** | (BOM) | Sistema de diseño |
| **Navigation 3** | 1.1.3 | Navegación entre pantallas |
| ![Room](https://img.shields.io/badge/-Room-FF6F00?logo=android&logoColor=white) **Room** | 2.8.4 | Base de datos local (v34, 21 entidades, 15 DAOs) |
| **SQLCipher** | 4.6.1 | Cifrado AES-256 de la base de datos Room |
| ![Koin](https://img.shields.io/badge/-Koin-F97316?logoColor=white) **Koin** | 4.2.2 | Inyección de dependencias |
| **Kotlin Coroutines + Flow** | 1.11.0 | Concurrencia y streams asíncronos |
| **Kotlin Serialization** | 1.11.0 | Serialización JSON |
| **DataStore Preferences** | 1.1.1 | Almacenamiento de preferencias de usuario |
| **WorkManager** | 2.11.2 | Ejecución de mensajes programados en background |
| **Paging 3** | 3.5.0 | Carga paginada de mensajes |
| **Biometric** | 1.2.0-alpha05 | Autenticación biométrica para el bloqueo de app |
| ![Coil](https://img.shields.io/badge/-Coil-000000?logoColor=white) **Coil 3** | 3.5.0 | Carga de imágenes, GIFs, stickers y vídeo (disk cache 50 MB + memory cache 20% heap) |
| **ML Kit Translate** | 17.0.3 | Traducción offline de mensajes (sin conexión a internet) |
| **QRCode Kotlin** | 4.1.1 | Generación de códigos QR de contacto |
| **ZXing Android Embedded** | 4.3.0 | Escáner de códigos QR para añadir contactos |
| **OkHttp** | 4.x | Cliente HTTP con certificate pinning |
| **Play Integrity API** | 1.4.0 | Verificación de integridad del dispositivo y la app |

### Backend / Servicios

| Tecnología | Versión | Uso |
|---|---|---|
| ![Supabase](https://img.shields.io/badge/-Supabase-3ECF8E?logo=supabase&logoColor=white) **Supabase** | 3.6.0 | PostgreSQL, Auth, Realtime, Storage y Edge Functions |
| ![Ktor](https://img.shields.io/badge/-Ktor-0095D5?logo=kotlin&logoColor=white) **Ktor Client** | 3.5.1 | Cliente HTTP |
| ![Firebase](https://img.shields.io/badge/-Firebase%20FCM-FFCA28?logo=firebase&logoColor=black) **Firebase Cloud Messaging** | BOM 34.15.0 | Notificaciones push |
| ![Google](https://img.shields.io/badge/-Google%20Sign--In-4285F4?logo=google&logoColor=white) **Credential Manager** | 1.6.0 | Autenticación con Google |
| ![LiveKit](https://img.shields.io/badge/-LiveKit-E5363B?logoColor=white) **LiveKit** | 2.26.1 | Llamadas de voz y vídeo WebRTC |
| **Giphy API** | — | Búsqueda y envío de GIFs |
| ![Deno](https://img.shields.io/badge/-Deno%20%2F%20TypeScript-000000?logo=deno&logoColor=white) **Deno / TypeScript** | — | Supabase Edge Functions (FCM, LiveKit token, Play Integrity, IA, assetlinks) |

### Testing

| Tecnología | Versión | Uso |
|---|---|---|
| **JUnit 4** | 4.13.2 | Framework de tests |
| ![MockK](https://img.shields.io/badge/-MockK-E14343?logoColor=white) **MockK** | 1.14.11 | Mocking en Kotlin |
| **Turbine** | 1.2.1 | Assertions sobre Flows |
| **Coroutines Test** | 1.11.0 | TestDispatcher y runTest |
| **Robolectric** | 4.16.1 | Tests unitarios con contexto Android |
| **Room Testing** | 2.8.4 | Tests de integración en memoria para DAOs |

**475 tests** repartidos en 59 ficheros:

**ViewModels**

| Fichero | Tests |
|---|---|
| `ChatViewModelTest` | 21 |
| `StatusViewModelTest` | 14 |
| `GroupInfoViewModelTest` | 12 |
| `CreateGroupViewModelTest` | 11 |
| `NewChatViewModelTest` | 10 |
| `InvitationsViewModelTest` | 7 |
| `UserInfoViewModelTest` | 6 |
| `ConversationListViewModelTest` | 5 |
| `GlobalSearchViewModelTest` | 5 |

**DAOs (Room in-memory)**

| Fichero | Tests |
|---|---|
| `ConversationDaoTest` | 18 |
| `MessageDaoTest` | 15 |
| `GroupMemberDaoTest` | 12 |
| `StatusDaoTest` | 10 |
| `ReactionDaoTest` | 9 |
| `InvitationDaoTest` | 7 |
| `UserDaoTest` | 8 |

**Repositorios**

| Fichero | Tests |
|---|---|
| `InvitationRepositoryImplTest` | 12 |
| `GroupRepositoryImplTest` | 11 |
| `UserRepositoryImplTest` | 8 |
| `PollRepositoryImplTest` | 7 |
| `ReactionRepositoryImplTest` | 5 |
| `BroadcastListRepositoryImplTest` | 5 |
| `CallRepositoryImplTest` | 3 |
| `MessageRepositoryImplTest` | 3 |

**Use Cases**

| Fichero | Tests |
|---|---|
| `SetUsernameUseCaseTest` | 12 |
| `SendMessageUseCaseTest` | 11 |
| `SendInvitationUseCaseTest` | 9 |
| `CreateGroupUseCaseTest` | 8 |
| `UpdateGroupUseCaseTest` | 7 |
| `BlockUserUseCaseTest` | 6 |
| `ExportConversationUseCaseTest` | 6 |
| `RespondInvitationUseCaseTest` | 4 |
| `ObserveConversationsUseCaseTest` | 4 |
| `GetCurrentUserUseCaseTest` | 4 |
| `PromoteGroupMemberUseCaseTest` | 4 |
| `GetOrCreateConversationUseCaseTest` | 3 |
| `LeaveGroupUseCaseTest` | 3 |
| `GetGroupMembersUseCaseTest` | 3 |
| `SearchUsersUseCaseTest` | 3 |
| `AddGroupMemberUseCaseTest` | 2 |
| `GetCacheFileUseCaseTest` | 2 |
| `GetDeviceContactsUseCaseTest` | 2 |
| `ObserveInvitationsUseCaseTest` | 2 |
| `ObserveMessagesUseCaseTest` | 2 |
| `RemoveGroupMemberUseCaseTest` | 2 |
| `GetUriMetadataUseCaseTest` | 1 |
| `ReadUriAsBytesUseCaseTest` | 1 |

**Mappers y modelos**

| Fichero | Tests |
|---|---|
| `MessageBOTest` | 22 |
| `MediaUrlValidatorTest` | 17 |
| `UserMapperTest` | 16 |
| `ConversationMapperTest` | 13 |
| `MessageMapperTest` | 13 |
| `InvitationMapperTest` | 10 |
| `GroupMapperTest` | 8 |
| `StatusMapperTest` | 5 |

**Utilidades y servicios**

| Fichero | Tests |
|---|---|
| `UploadLimitsTest` | 18 |
| `FcmMessageHandlerTest` | 19 |
| `GiphyKeyManagerTest` | 5 |
| `CatchResultTest` | 4 |

### CI/CD

| Herramienta | Uso |
|---|---|
| ![GitHub Actions](https://img.shields.io/badge/-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white) **GitHub Actions** | Pipeline paralelo en cada push: unit tests + cobertura Jacoco, Android Lint, Detekt, build debug y release |
| ![GitHub Secrets](https://img.shields.io/badge/-GitHub%20Secrets-181717?logo=github&logoColor=white) **GitHub Secrets** | Gestión segura de claves (Supabase, Firebase, LiveKit, Giphy) |
| **Detekt 1.23.8** | Análisis estático de Kotlin con baseline para código heredado |
| **Jacoco** | Cobertura de tests unitarios generada en cada CI run |
| **OWASP Dependency Check** | Escaneo semanal de dependencias con vulnerabilidades conocidas (CVE ≥ 7.0) |
| **Dependency Update workflow** | Regenera `gradle/verification-metadata.xml` semanalmente y abre PR automático a `develop` si hay cambios |

---

## 🚀 Setup local

> Requiere Android 9 (API 28) o superior — `minSdk = 28`, `targetSdk = 37`.

1. Clona el repositorio
2. Copia `local.properties.example` → `local.properties` y rellena tus claves:

```
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
GOOGLE_WEB_CLIENT_ID=...
LIVEKIT_URL=...
GIPHY_API_KEY=...
```

3. Descarga tu `google-services.json` de [Firebase Console](https://console.firebase.google.com) y colócalo en `app/`
4. Abre el proyecto en Android Studio y ejecuta:

```bash
./gradlew assembleDebug
```

---

## 🌿 Estructura de ramas (Gitflow)

```
master        ← releases estables (v1.0, v1.1…)
└── develop   ← integración continua
    ├── feature/…                  (60+ feature branches de funcionalidad)
    ├── feature/emoji-picker
    ├── feature/message-reactions
    ├── feature/message-search
    ├── feature/edit-messages
    ├── feature/deep-links
    ├── feature/supabase-presence-migration
    ├── feature/coil-disk-cache
    ├── feature/camera-switch-call
    ├── feature/notification-reply
    ├── feature/mute-snooze
    ├── feature/self-destruct
    ├── feature/room-integration-tests
    ├── feature/strictmode-debug
    ├── feature/attachment-bottom-sheet
    ├── feature/link-preview
    ├── feature/audio-playback-speed
    ├── feature/dark-mode-setting
    ├── feature/forward-message
    ├── feature/typing-indicator
    ├── feature/archive-chats
    ├── feature/shared-media-gallery
    ├── feature/chat-viewmodel-tests
    ├── feature/group-roles
    ├── fix/viewmodel-coroutine-leaks
    ├── fix/e2ee-key-cache
    ├── fix/edge-to-edge-insets
    ├── ci/improvements
    ├── security/flag-secure
    ├── security/backup-rules
    ├── security/exported-components
    ├── security/play-integrity
    ├── security/session-revocation
    ├── security/storage-size-limits
    ├── security/proguard-obfuscation
    ├── security/dependency-pinning
    ├── security/coil-certificate-pinning
    ├── security/log-sanitization
    ├── security/message-length-validation
    ├── security/edge-function-rate-limiting
    ├── security/intent-validation
    ├── security/sticker-url-validation
    ├── security/media-url-whitelist
    ├── security/play-integrity-enforcement
    ├── security/deep-link-verification
    ├── security/postgres-grants-audit
    ├── security/clipboard-protection
    ├── security/certificate-transparency
    ├── security/session-expiration
    ├── security/root-detection
    ├── security/e2ee-messages
    ├── feature/in-call-chat
    ├── feature/location-sharing
    ├── feature/screen-sharing
    ├── feature/message-drafts
    ├── feature/message-translation
    ├── feature/custom-notification-sounds
    ├── feature/audio-transcription
    ├── feature/video-blur-background
    ├── feature/pinned-messages
    ├── feature/saved-messages
    ├── feature/group-polls
    ├── feature/sticker-packs
    ├── feature/chat-themes
    ├── feature/contact-qr
    ├── feature/export-conversation
    ├── feature/contact-sync
    ├── feature/2fa
    └── feature/disappearing-mode
```

> **Nota para desarrollo:** Las notificaciones push FCM no funcionan en emuladores a menos que el SHA-1 del debug keystore esté registrado en Firebase Console. Ejecuta `./gradlew signingReport` para obtener el SHA-1 y añádelo en Firebase Console → Configuración del proyecto → Tus apps → Android.
