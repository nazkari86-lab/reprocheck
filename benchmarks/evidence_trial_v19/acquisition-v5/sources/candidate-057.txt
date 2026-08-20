# US Counties Healthcare Analysis Dashboard

An interactive web application for analyzing healthcare access and socioeconomic factors across US counties. This project combines comprehensive data analysis with an intuitive map-based interface to explore healthcare disparities and policy implications.

## Features

### 🗺️ **Interactive Map Visualization**
- **Choropleth mapping** of healthcare access scores across all US counties
- **Multiple visualization modes**: Healthcare Access, Opportunity Score, Vulnerability Index
- **Real-time filtering** by region, population, income, and other socioeconomic factors
- **County selection** with detailed information panels

### 📊 **Advanced Analysis Tools**
- **Peer Comparison Analysis**: Compare counties with similar characteristics
- **Policy Impact Simulation**: Model effects of healthcare policy changes
- **Future Projections**: 5-year healthcare access trend analysis
- **AI-Powered Recommendations**: Personalized policy suggestions using Groq Llama API

### 🎛️ **Comprehensive Filtering System**
- **Geographic filters**: Region, population range
- **Healthcare metrics**: Access score, insurance coverage, disability rate
- **Socioeconomic factors**: Income, poverty, education rates
- **Infrastructure**: Broadband access, resilience scores

### 🤖 **AI Integration**
- **Groq Llama API** for intelligent county-specific recommendations
- **Fallback system** with rule-based recommendations when AI unavailable
- **Caching mechanism** for improved performance
- **Manual API key input** for user customization

## Tech Stack

- **Frontend**: React 19, Vite, Tailwind CSS
- **Mapping**: Leaflet, React-Leaflet
- **Animations**: Framer Motion
- **AI**: Groq Llama API
- **Data**: JSON-based county healthcare datasets

## Getting Started

### Prerequisites
- Node.js 18+
- npm or pnpm

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd results
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   ```

3. **Configure AI (Optional)**
   ```bash
   # Create .env file
   echo "VITE_GROQ_API_KEY=your_groq_api_key_here" > .env
   ```
   Or use the in-app API key input for manual configuration.

4. **Start development server**
   ```bash
   pnpm dev
   ```

5. **Open your browser**
   ```
   http://localhost:5173
   ```

## Deployment

### GitHub Pages
The project includes automated deployment to GitHub Pages:

```bash
# Build for production
pnpm run build

# Deploy to GitHub Pages
pnpm run deploy
```

### Manual Deployment
1. Build the project: `pnpm run build`
2. Upload the `dist` folder to your hosting service
3. For AI functionality, inject the API key at runtime or use the in-app configuration

## Data Sources

The application uses comprehensive healthcare and socioeconomic data including:
- County Health Rankings & Roadmaps
- US Census Bureau data
- CDC health indicators
- Socioeconomic and demographic metrics

## Architecture

```
src/
├── components/          # React components
│   ├── MapView.jsx     # Interactive county map
│   ├── AnalysisPanel.jsx # AI analysis interface
│   ├── AdvancedControls.jsx # Filtering controls
│   └── ...
├── utils/              # Utility functions
│   └── aiRecommendations.js # AI integration
└── data/               # Static data files
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of a technical assessment submission.
