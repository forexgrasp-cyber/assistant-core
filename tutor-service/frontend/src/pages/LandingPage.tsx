import { Link } from 'react-router-dom'
import { 
  Brain, 
  Mic, 
  BookOpen, 
  Target, 
  Zap, 
  Globe, 
  Award, 
  Users,
  CheckCircle,
  ArrowRight,
  Star,
  BarChart2,
  MessageSquare,
  Headphones,
  GraduationCap,
  Shield,
  Clock
} from 'lucide-react'
import { motion } from 'framer-motion'

const features = [
  {
    icon: Brain,
    title: 'AI-Powered Personal Tutor',
    description: 'GPT-4 powered tutor that adapts to your learning style, pace, and goals. Get personalized explanations, practice exercises, and real-time feedback.',
    benefit: 'Learn 3x faster than traditional methods'
  },
  {
    icon: Mic,
    title: 'Full Voice Conversation',
    description: 'Speak naturally with your tutor using advanced speech recognition and synthesis. Practice pronunciation with AI evaluation and accent coaching.',
    benefit: 'Native-like pronunciation in weeks'
  },
  {
    icon: BookOpen,
    title: 'Structured Curriculum (A1-C2)',
    description: 'CEFR-aligned lessons across 70+ languages. From beginner to mastery with grammar, vocabulary, culture, and real-world scenarios.',
    benefit: 'Clear path from zero to fluency'
  },
  {
    icon: Target,
    title: 'Smart Lesson Generation',
    description: 'AI creates custom lessons from YouTube, textbooks, and web content tailored to your gaps. Never study what you already know.',
    benefit: '100% relevant content, zero waste'
  },
  {
    icon: Zap,
    title: 'Mixed-Mode Learning',
    description: 'Seamlessly switch between speaking, writing, listening, and reading. Your tutor tracks progress across all modalities.',
    benefit: 'Complete language competency'
  },
  {
    icon: Globe,
    title: '70+ Languages Supported',
    description: 'From Spanish and French to Japanese, Korean, Arabic, and more. Each with native voices, cultural context, and localized curriculum.',
    benefit: 'Any language, one platform'
  }
]

const benefits = [
  { icon: CheckCircle, text: 'Personalized study plan based on your goals and schedule' },
  { icon: CheckCircle, text: 'Real-time pronunciation scoring with IPA feedback' },
  { icon: CheckCircle, text: 'Writing correction with grammar explanations' },
  { icon: CheckCircle, text: 'Spaced repetition vocabulary system' },
  { icon: CheckCircle, text: 'Cultural insights and idiom mastery' },
  { icon: CheckCircle, text: 'Progress tracking with CEFR milestone certificates' },
  { icon: CheckCircle, text: 'Offline-first PWA — learn anywhere, anytime' },
  { icon: CheckCircle, text: 'Gamified with streaks, leagues, and achievements' },
  { icon: CheckCircle, text: 'Private by design — your data never sold' }
]

const stats = [
  { value: '70+', label: 'Languages' },
  { value: '18', label: 'CEFR Levels' },
  { value: '50K+', label: 'Lessons Generated' },
  { value: '4.9★', label: 'User Rating' }
]

const testimonials = [
  {
    quote: "Finally, a language app that actually teaches you to SPEAK. The AI tutor corrects my pronunciation in real-time and the conversations feel natural. Went from A2 to B1 Spanish in 3 months.",
    author: 'Sarah Chen',
    role: 'Software Engineer',
    language: 'Spanish',
    progress: 'A2 → B1 in 3 months'
  },
  {
    quote: "The custom lesson generation is a game-changer. I upload YouTube videos about my industry and get tailored business French lessons. My clients noticed the difference immediately.",
    author: 'Marcus Johnson',
    role: 'International Sales Director',
    language: 'French',
    progress: 'B1 → B2 in 4 months'
  },
  {
    quote: "My 8-year-old loves the child track — it's like having a patient native speaker tutor 24/7. The gamification keeps her engaged and she's now teaching ME Japanese phrases!",
    author: 'Yuki Tanaka',
    role: 'Parent',
    language: 'Japanese (Child Track)',
    progress: 'Zero to A1 in 6 weeks'
  }
]

const pricingTiers = [
  {
    name: 'Free',
    price: '$0',
    period: '/month',
    description: 'Perfect for trying out the platform',
    features: [
      'Access to 3 languages',
      '10 AI conversations/month',
      'Basic curriculum (A1-A2)',
      'Speech recognition practice',
      'Progress tracking',
      'Community support'
    ],
    cta: 'Start Free',
    popular: false
  },
  {
    name: 'Pro',
    price: '$19',
    period: '/month',
    description: 'For serious language learners',
    features: [
      'All 70+ languages',
      'Unlimited AI conversations',
      'Full curriculum (A1-C2)',
      'Pronunciation evaluation & coaching',
      'Writing correction with explanations',
      'Custom lesson generation',
      'Offline sync & PWA',
      'Priority support',
      'CEFR certificates'
    ],
    cta: 'Get Pro',
    popular: true
  },
  {
    name: 'Family',
    price: '$39',
    period: '/month',
    description: 'Up to 5 family members',
    features: [
      'Everything in Pro',
      '5 separate profiles',
      'Child-safe mode with gamification',
      'Family progress dashboard',
      'Shared vocabulary lists',
      'Parental controls & reports',
      'Custom family curriculum'
    ],
    cta: 'Start Family Plan',
    popular: false
  }
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-xl border-b border-gray-100">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" aria-label="Main navigation">
          <div className="flex h-16 items-center justify-between">
            <Link to="/" className="flex items-center gap-2" aria-label="LinguaFlow Home">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary-600 to-primary-800">
                <GraduationCap className="h-5 w-5 text-white" aria-hidden="true" />
              </div>
              <span className="font-display font-bold text-xl text-gray-900">LinguaFlow</span>
            </Link>
            
            <div className="hidden md:flex items-center gap-8">
              <Link to="#features" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Features</Link>
              <Link to="#languages" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Languages</Link>
              <Link to="#how-it-works" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">How It Works</Link>
              <Link to="#pricing" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Pricing</Link>
              <Link to="#testimonials" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Reviews</Link>
            </div>
            
            <div className="hidden md:flex items-center gap-4">
              <Link to="/login" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">Sign In</Link>
              <Link to="/register" className="btn-primary text-sm px-5 py-2.5">Get Started Free</Link>
            </div>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden" aria-labelledby="hero-heading">
        <div className="absolute inset-0 bg-gradient-to-b from-primary-50 via-white to-white" aria-hidden="true" />
        <div className="absolute top-0 left-0 right-0 h-1/2 bg-gradient-to-b from-primary-100/50 to-transparent" aria-hidden="true" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            <div className="text-center lg:text-left">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-50 text-primary-700 text-sm font-medium mb-6"
              >
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500" />
                </span>
                New: AI Lesson Generator from YouTube & Textbooks
              </motion.div>
              
              <h1
                id="hero-heading"
                className="text-4xl sm:text-5xl lg:text-6xl font-display font-bold text-gray-900 leading-tight mb-6"
              >
                Master Any Language with{' '}
                <span className="bg-gradient-to-r from-primary-600 to-primary-800 bg-clip-text text-transparent">
                  Your Personal AI Tutor
                </span>
              </h1>
              
              <p className="text-lg sm:text-xl text-gray-600 mb-8 max-w-xl mx-auto lg:mx-0">
                Speak from day one. Get real-time pronunciation coaching. 
                Learn with custom lessons generated from content you love. 
                Join 50,000+ learners reaching fluency faster.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4 mb-12">
                <Link
                  to="/register"
                  className="btn-primary lg:w-auto w-full px-8 py-4 text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-200 group"
                >
                  Start Learning Free
                  <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" aria-hidden="true" />
                </Link>
                <Link
                  to="#demo"
                  className="btn-secondary lg:w-auto w-full px-8 py-4 text-lg font-semibold transition-all duration-200"
                >
                  Watch Demo
                </Link>
              </div>
              
              <div className="flex flex-wrap items-center justify-center lg:justify-start gap-6 text-sm text-gray-500">
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="h-5 w-5 text-green-500" aria-hidden="true" />
                  <span>No credit card required</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="h-5 w-5 text-green-500" aria-hidden="true" />
                  <span>14-day Pro trial</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="h-5 w-5 text-green-500" aria-hidden="true" />
                  <span>Cancel anytime</span>
                </div>
              </div>
            </div>
            
            {/* Hero Visual */}
            <div className="relative" aria-hidden="true">
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="relative bg-white rounded-3xl shadow-2xl border border-gray-100 p-4 max-w-md mx-auto"
              >
                {/* Mock chat interface */}
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-2xl">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100">
                      <Brain className="h-5 w-5 text-primary-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 text-sm">AI Tutor</p>
                      <p className="text-sm text-gray-500">Ready to practice Spanish?</p>
                    </div>
                  </div>
                  
                  <div className="flex items-end gap-3 justify-end">
                    <div className="max-w-[70%]">
                      <div className="bg-primary-600 text-white rounded-2xl rounded-br-md px-4 py-3">
                        <p className="text-sm">¡Hola! I'm ready when you are. Want to practice ordering at a restaurant?</p>
                      </div>
                      <div className="flex items-center gap-1 mt-1 text-xs text-gray-400">
                        <Mic className="h-3 w-3" />
                        <span>Press to speak</span>
                      </div>
                    </div>
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100">
                      <span className="text-xs font-medium text-gray-600">You</span>
                    </div>
                  </div>
                  
                  <div className="flex items-end gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100">
                      <Brain className="h-4 w-4 text-primary-600" />
                    </div>
                    <div className="max-w-[70%]">
                      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                        <p className="text-sm text-gray-900">Perfect! Let's start with: "Quisiera una mesa para dos, por favor."</p>
                        <div className="mt-2 flex items-center gap-2 text-xs">
                          <span className="px-2 py-1 bg-green-50 text-green-700 rounded-full">Pronunciation: 94%</span>
                          <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full">Grammar: ✓</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3 justify-end">
                    <div className="max-w-[70%]">
                      <div className="bg-primary-600 text-white rounded-2xl rounded-br-md px-4 py-3">
                        <p className="text-sm">Quisiera una mesa para dos, por favor.</p>
                      </div>
                    </div>
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100">
                      <span className="text-xs font-medium text-gray-600">You</span>
                    </div>
                  </div>
                  
                  <div className="flex items-end gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100">
                      <Brain className="h-4 w-4 text-primary-600" />
                    </div>
                    <div className="max-w-[70%]">
                      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                        <p className="text-sm text-gray-900">¡Excelente! Your pronunciation was near-native. The 'r' in 'para' was perfect. Ready for the next scenario?</p>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Floating stats */}
                <div className="absolute -bottom-6 -left-6 bg-white rounded-2xl shadow-xl p-4 border border-gray-100 animate-bounce-gentle">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-100">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <p className="font-bold text-gray-900">+94% Pronunciation</p>
                      <p className="text-xs text-gray-500">After 2 weeks</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </div>
        
        {/* Trust indicators */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-8 text-sm text-gray-500" aria-hidden="true">
          <div className="flex items-center gap-2">
            <Star className="h-4 w-4 text-yellow-400 fill-current" />
            <span>4.9/5</span>
          </div>
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            <span>50K+ learners</span>
          </div>
          <div className="flex items-center gap-2">
            <Award className="h-4 w-4" />
            <span>#1 AI Language App</span>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="py-16 bg-gray-900 text-white" aria-labelledby="stats-heading">
        <h2 id="stats-heading" className="sr-only">Platform Statistics</h2>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="text-center"
              >
                <p className="text-4xl sm:text-5xl font-display font-bold bg-gradient-to-r from-primary-400 to-primary-600 bg-clip-text text-transparent">
                  {stat.value}
                </p>
                <p className="text-gray-400 mt-1">{stat.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 lg:py-32 bg-white" aria-labelledby="features-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 id="features-heading" className="text-3xl sm:text-4xl font-display font-bold text-gray-900 mb-4">
              Everything You Need to Reach Fluency
            </h2>
            <p className="text-lg text-gray-600">
              Built by language learners, for language learners. Every feature designed to get you speaking confidently.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, i) => (
              <motion.article
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="group p-6 rounded-2xl bg-gray-50 hover:bg-white hover:shadow-xl transition-all duration-300 border border-gray-100"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-100 text-primary-600 mb-4 group-hover:scale-110 transition-transform">
                  <feature.icon className="h-6 w-6" aria-hidden="true" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-600 mb-4">{feature.description}</p>
                <div className="flex items-center gap-2 text-primary-600 font-medium text-sm">
                  <span>{feature.benefit}</span>
                  <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                </div>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits List */}
      <section className="py-24 lg:py-32 bg-gray-50" aria-labelledby="benefits-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-start">
            <div>
              <h2 id="benefits-heading" className="text-3xl sm:text-4xl font-display font-bold text-gray-900 mb-6">
                Why Learners Choose LinguaFlow
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                Traditional apps teach you to recognize words. We teach you to communicate. 
                Every feature is built around the science of language acquisition.
              </p>
              
              <div className="space-y-4">
                {benefits.map((benefit, i) => (
                  <motion.div
                    key={benefit.text}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true, margin: '-50px' }}
                    transition={{ duration: 0.4, delay: i * 0.05 }}
                    className="flex items-start gap-3 p-4 bg-white rounded-xl border border-gray-100 hover:shadow-md transition-shadow"
                  >
                    <div className="flex-shrink-0 flex h-8 w-8 items-center justify-center rounded-lg bg-green-100">
                      <benefit.icon className="h-5 w-5 text-green-600" aria-hidden="true" />
                    </div>
                    <p className="text-gray-700 font-medium">{benefit.text}</p>
                  </motion.div>
                ))}
              </div>
            </div>
            
            <div className="relative" aria-hidden="true">
              <div className="aspect-square relative max-w-lg mx-auto">
                <svg viewBox="0 0 400 400" className="w-full h-full">
                  <defs>
                    <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#3B82F6" />
                      <stop offset="100%" stopColor="#8B5CF6" />
                    </linearGradient>
                  </defs>
                  {/* Background circles */}
                  <circle cx="200" cy="200" r="180" stroke="#E5E7EB" strokeWidth="12" fill="none" />
                  <circle cx="200" cy="200" r="140" stroke="#E5E7EB" strokeWidth="12" fill="none" />
                  <circle cx="200" cy="200" r="100" stroke="#E5E7EB" strokeWidth="12" fill="none" />
                  <circle cx="200" cy="200" r="60" stroke="#E5E7EB" strokeWidth="12" fill="none" />
                  
                  {/* Progress circles */}
                  <circle 
                    cx="200" cy="200" r="180" 
                    stroke="url(#progressGradient)" strokeWidth="12" fill="none" 
                    strokeDasharray="1131" strokeDashoffset="226"
                    strokeLinecap="round"
                    className="animate-progress"
                  />
                  <circle 
                    cx="200" cy="200" r="140" 
                    stroke="#3B82F6" strokeWidth="12" fill="none" 
                    strokeDasharray="880" strokeDashoffset="176"
                    strokeLinecap="round"
                    className="animate-progress"
                    style={{ animationDelay: '0.5s' }}
                  />
                  <circle 
                    cx="200" cy="200" r="100" 
                    stroke="#8B5CF6" strokeWidth="12" fill="none" 
                    strokeDasharray="628" strokeDashoffset="63"
                    strokeLinecap="round"
                    className="animate-progress"
                    style={{ animationDelay: '1s' }}
                  />
                  <circle 
                    cx="200" cy="200" r="60" 
                    stroke="#10B981" strokeWidth="12" fill="none" 
                    strokeDasharray="377" strokeDashoffset="0"
                    strokeLinecap="round"
                    className="animate-progress"
                    style={{ animationDelay: '1.5s' }}
                  />
                </svg>
                
                {/* Milestone labels */}
                <div className="absolute top-4 left-1/2 -translate-x-1/2 text-center">
                  <p className="text-2xl font-bold text-primary-600">C1</p>
                  <p className="text-xs text-gray-500">Advanced</p>
                </div>
                <div className="absolute top-1/2 right-4 -translate-y-1/2 text-center">
                  <p className="text-xl font-bold text-blue-600">B2</p>
                  <p className="text-xs text-gray-500">Upper Intermediate</p>
                </div>
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-center">
                  <p className="text-xl font-bold text-purple-600">B1</p>
                  <p className="text-xs text-gray-500">Intermediate</p>
                </div>
                <div className="absolute top-1/2 left-4 -translate-y-1/2 text-center">
                  <p className="text-lg font-bold text-green-600">A2</p>
                  <p className="text-xs text-gray-500">Elementary</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Languages */}
      <section id="languages" className="py-24 lg:py-32 bg-white" aria-labelledby="languages-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 id="languages-heading" className="text-3xl sm:text-4xl font-display font-bold text-gray-900 mb-4">
              70+ Languages, One Platform
            </h2>
            <p className="text-lg text-gray-600">
              From the world's most spoken languages to less common ones. 
              Each with native AI voices, cultural context, and CEFR-aligned curriculum.
            </p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {[
              { code: 'es', name: 'Spanish', native: 'Español', learners: '500M+' },
              { code: 'fr', name: 'French', native: 'Français', learners: '300M+' },
              { code: 'de', name: 'German', native: 'Deutsch', learners: '130M+' },
              { code: 'it', name: 'Italian', native: 'Italiano', learners: '85M+' },
              { code: 'pt', name: 'Portuguese', native: 'Português', learners: '260M+' },
              { code: 'ja', name: 'Japanese', native: '日本語', learners: '125M+' },
              { code: 'ko', name: 'Korean', native: '한국어', learners: '80M+' },
              { code: 'zh', name: 'Chinese', native: '中文', learners: '1.1B+' },
              { code: 'ar', name: 'Arabic', native: 'العربية', learners: '420M+' },
              { code: 'ru', name: 'Russian', native: 'Русский', learners: '260M+' },
              { code: 'hi', name: 'Hindi', native: 'हिन्दी', learners: '600M+' },
              { code: 'nl', name: 'Dutch', native: 'Nederlands', learners: '25M+' },
              { code: 'pl', name: 'Polish', native: 'Polski', learners: '45M+' },
              { code: 'tr', name: 'Turkish', native: 'Türkçe', learners: '85M+' },
              { code: 'sv', name: 'Swedish', native: 'Svenska', learners: '10M+' },
              { code: 'he', name: 'Hebrew', native: 'עברית', learners: '9M+' },
            ].map((lang) => (
              <motion.button
                key={lang.code}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ duration: 0.3 }}
                className="group p-4 rounded-xl bg-gray-50 hover:bg-primary-50 border border-gray-100 hover:border-primary-200 transition-all text-left"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl" role="img" aria-label={lang.name}>
                    {lang.code === 'es' && '🇪🇸'}
                    {lang.code === 'fr' && '🇫🇷'}
                    {lang.code === 'de' && '🇩🇪'}
                    {lang.code === 'it' && '🇮🇹'}
                    {lang.code === 'pt' && '🇵🇹'}
                    {lang.code === 'ja' && '🇯🇵'}
                    {lang.code === 'ko' && '🇰🇷'}
                    {lang.code === 'zh' && '🇨🇳'}
                    {lang.code === 'ar' && '🇸🇦'}
                    {lang.code === 'ru' && '🇷🇺'}
                    {lang.code === 'hi' && '🇮🇳'}
                    {lang.code === 'nl' && '🇳🇱'}
                    {lang.code === 'pl' && '🇵🇱'}
                    {lang.code === 'tr' && '🇹🇷'}
                    {lang.code === 'sv' && '🇸🇪'}
                    {lang.code === 'he' && '🇮🇱'}
                  </span>
                  <div>
                    <p className="font-semibold text-gray-900">{lang.name}</p>
                    <p className="text-xs text-gray-500">{lang.native}</p>
                  </div>
                </div>
                <p className="text-xs text-gray-500">{lang.learners} speakers</p>
              </motion.button>
            ))}
          </div>
          
          <div className="text-center mt-12">
            <Link to="/register" className="btn-secondary inline-flex items-center gap-2">
              View All 70+ Languages
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 lg:py-32 bg-gray-50" aria-labelledby="how-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 id="how-heading" className="text-3xl sm:text-4xl font-display font-bold text-gray-900 mb-4">
              Start Speaking in 3 Steps
            </h2>
            <p className="text-lg text-gray-600">
              No placement tests, no rigid paths. Just tell us your goals and start learning.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                title: 'Tell Us Your Goals',
                description: 'Pick your target language, current level, and why you\'re learning — travel, work, family, or fun.',
                icon: Target,
                details: ['CEFR level assessment (optional)', 'Choose focus: conversation, business, travel, academic', 'Set your weekly time commitment']
              },
              {
                step: '02',
                title: 'Meet Your AI Tutor',
                description: 'Start your first conversation immediately. Your tutor adapts to your level and learning style.',
                icon: MessageSquare,
                details: ['Voice or text — your choice', 'Real-time pronunciation feedback', 'Personalized lesson plan generated']
              },
              {
                step: '03',
                title: 'Track Progress & Level Up',
                description: 'Watch your skills grow with detailed analytics. Earn certificates at each CEFR milestone.',
                icon: BarChart2,
                details: ['Vocabulary & grammar mastery tracking', 'Pronunciation improvement charts', 'CEFR certificates at each level']
              }
            ].map((step, i) => (
              <motion.article
                key={step.step}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.6, delay: i * 0.15 }}
                className="relative p-8 bg-white rounded-2xl border border-gray-100"
              >
                <div className="absolute -top-3 left-8 flex h-12 w-12 items-center justify-center rounded-full bg-primary-600 text-white font-bold text-lg">
                  {step.step}
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-100 text-primary-600 mb-4">
                  <step.icon className="h-6 w-6" aria-hidden="true" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{step.title}</h3>
                <p className="text-gray-600 mb-6">{step.description}</p>
                <ul className="space-y-2" role="list">
                  {step.details.map((detail, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-gray-600">
                      <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
                      {detail}
                    </li>
                  ))}
                </ul>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="py-24 lg:py-32 bg-white" aria-labelledby="testimonials-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 id="testimonials-heading" className="text-3xl sm:text-4xl font-display font-bold text-gray-900 mb-4">
              Trusted by 50,000+ Language Learners
            </h2>
            <p className="text-lg text-gray-600">
              Real people. Real results. See what our community has achieved.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, i) => (
              <motion.article
                key={testimonial.author}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.6, delay: i * 0.15 }}
                className="p-8 bg-gray-50 rounded-2xl border border-gray-100 hover:shadow-xl transition-shadow"
              >
                <div className="flex items-center gap-1 mb-4" aria-label="5 star rating">
                  {[...Array(5)].map((_, j) => (
                    <Star key={j} className="h-5 w-5 text-yellow-400 fill-current" aria-hidden="true" />
                  ))}
                </div>
                <blockquote className="text-gray-700 mb-6 leading-relaxed">
                  &ldquo;{testimonial.quote}&rdquo;
                </blockquote>
                <div className="border-t border-gray-200 pt-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100">
                      <span className="font-semibold text-primary-700">
                        {testimonial.author.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">{testimonial.author}</p>
                      <p className="text-sm text-gray-500">{testimonial.role}</p>
                    </div>
                  </div>
                  <div className="mt-4 p-3 bg-primary-50 rounded-xl">
                    <p className="text-sm font-medium text-primary-700">{testimonial.language}</p>
                    <p className="text-sm text-primary-600">{testimonial.progress}</p>
                  </div>
                </div>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 lg:py-32 bg-gray-50" aria-labelledby="pricing-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 id="pricing-heading" className="text-3xl sm:text-4xl font-display font-bold text-gray-900 mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-lg text-gray-600">
              Start free. Upgrade when you're ready. No hidden fees, cancel anytime.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {pricingTiers.map((tier, i) => (
              <motion.article
                key={tier.name}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.6, delay: i * 0.15 }}
                className={`relative p-8 rounded-2xl ${
                  tier.popular 
                    ? 'bg-primary-600 text-white shadow-2xl ring-4 ring-primary-200' 
                    : 'bg-white text-gray-900 border border-gray-100 hover:shadow-xl transition-shadow'
                }`}
              >
                {tier.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-yellow-400 text-gray-900 text-sm font-semibold rounded-full">
                    Most Popular
                  </div>
                )}
                
                <div className="mb-6">
                  <h3 className={`text-xl font-semibold ${tier.popular ? 'text-white' : 'text-gray-900'}`}>{tier.name}</h3>
                  <div className="flex items-baseline gap-1 mt-2">
                    <span className={`text-4xl font-bold ${tier.popular ? 'text-white' : 'text-gray-900'}`}>{tier.price}</span>
                    <span className={`text-gray-400 ${tier.popular ? 'text-primary-100' : ''}`}>{tier.period}</span>
                  </div>
                  <p className={`text-sm mt-2 ${tier.popular ? 'text-primary-100' : 'text-gray-500'}`}>{tier.description}</p>
                </div>
                
                <ul className="space-y-3 mb-8" role="list">
                  {tier.features.map((feature, j) => (
                    <li key={j} className="flex items-start gap-3">
                      <CheckCircle className={`h-5 w-5 flex-shrink-0 mt-0.5 ${tier.popular ? 'text-primary-200' : 'text-green-500'}`} aria-hidden="true" />
                      <span className={`text-sm ${tier.popular ? 'text-primary-50' : 'text-gray-600'}`}>{feature}</span>
                    </li>
                  ))}
                </ul>
                
                <Link
                  to="/register"
                  className={`block w-full text-center py-3 px-4 rounded-xl font-semibold transition-all duration-200 ${
                    tier.popular
                      ? 'bg-white text-primary-600 hover:bg-primary-50'
                      : 'bg-primary-600 text-white hover:bg-primary-700'
                  }`}
                >
                  {tier.cta}
                </Link>
              </motion.article>
            ))}
          </div>
          
          <p className="text-center text-gray-500 mt-8 text-sm">
            All plans include 14-day Pro trial. No credit card required. 
            <Link to="#faq" className="text-primary-600 hover:underline font-medium">View FAQ</Link>
          </p>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 lg:py-32 bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 text-white" aria-labelledby="cta-heading">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 id="cta-heading" className="text-3xl sm:text-4xl lg:text-5xl font-display font-bold mb-6">
            Ready to Start Your Language Journey?
          </h2>
          <p className="text-lg sm:text-xl text-primary-100 mb-10 max-w-2xl mx-auto">
            Join 50,000+ learners who are already speaking confidently. 
            Your first conversation starts in 30 seconds.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/register"
              className="btn-primary bg-white text-primary-600 hover:bg-primary-50 px-8 py-4 text-lg font-semibold shadow-lg w-full sm:w-auto"
            >
              Start Free — No Credit Card
            </Link>
            <Link
              to="#demo"
              className="btn-secondary border-white/30 text-white hover:bg-white/10 px-8 py-4 text-lg font-semibold w-full sm:w-auto"
            >
              See How It Works
            </Link>
          </div>
          <p className="mt-6 text-primary-200 text-sm">
            Free forever for basic use • 14-day Pro trial • Cancel anytime • GDPR compliant
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-300 py-16" role="contentinfo">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div className="md:col-span-2">
              <Link to="/" className="flex items-center gap-2 mb-4" aria-label="LinguaFlow Home">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary-600 to-primary-800">
                  <GraduationCap className="h-5 w-5 text-white" aria-hidden="true" />
                </div>
                <span className="font-display font-bold text-xl text-white">LinguaFlow</span>
              </Link>
              <p className="text-gray-400 max-w-xs mb-6">
                The AI language tutor that gets you speaking from day one. 
                Personalized, adaptive, and built for real fluency.
              </p>
              <div className="flex gap-4">
                <a href="#" className="text-gray-400 hover:text-white transition-colors" aria-label="Twitter">
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24"><path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4a4.5 4.5 0 0 0 1.5 7.5 4.5 4.5 0 0 1-2-3.5v.05a4.5 4.5 0 0 0 4.5 4.5 4.5 4.5 0 0 1-2-0.08 4.5 4.5 0 0 0 4.2 3 8.9 8.9 0 0 1-5.5 1.5 12.8 12.8 0 0 0 6.9 2 12.9 12.9 0 0 0 6.5-2.5" /></svg>
                </a>
                <a href="#" className="text-gray-400 hover:text-white transition-colors" aria-label="GitHub">
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
                </a>
                <a href="#" className="text-gray-400 hover:text-white transition-colors" aria-label="Discord">
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.675 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.083.083 0 0 0 .031.057 19.9 19.9 0 0 0 5.992 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.007-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.645.77 1.255 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054A19.577 19.577 0 0 0 20.317 4.37zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333 1.007-2.419 2.157-2.419 1.165 0 2.156 1.095 2.156 2.42 0 1.333-.99 2.418-2.156 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333 1.007-2.419 2.157-2.419 1.152 0 2.142 1.095 2.142 2.42 0 1.333-.99 2.418-2.142 2.418z"/></svg>
                </a>
              </div>
            </div>
            
            <div>
              <h4 className="font-semibold text-white mb-4">Product</h4>
              <ul className="space-y-2" role="list">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#languages" className="hover:text-white transition-colors">Languages</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href="#demo" className="hover:text-white transition-colors">Demo</a></li>
                <li><a href="#" className="hover:text-white transition-colors">API Docs</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold text-white mb-4">Company</h4>
              <ul className="space-y-2" role="list">
                <li><a href="#" className="hover:text-white transition-colors">About</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Press</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold text-white mb-4">Legal</h4>
              <ul className="space-y-2" role="list">
                <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Cookie Policy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Security</a></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-gray-500 text-sm">
              © 2026 LinguaFlow. All rights reserved.
            </p>
            <div className="flex items-center gap-6 text-sm text-gray-500">
              <a href="#" className="hover:text-white transition-colors">Privacy</a>
              <a href="#" className="hover:text-white transition-colors">Terms</a>
              <a href="#" className="hover:text-white transition-colors">Cookies</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

// Add keyframes for progress animation
const style = document.createElement('style')
style.textContent = `
  @keyframes progress {
    from { stroke-dashoffset: 1131; }
    to { stroke-dashoffset: 0; }
  }
  .animate-progress {
    animation: progress 2s ease-out forwards;
  }
  @keyframes bounce-gentle {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-4px); }
  }
  .animate-bounce-gentle {
    animation: bounce-gentle 2s ease-in-out infinite;
  }
`
if (typeof document !== 'undefined') {
  document.head.appendChild(style)
}