declare module 'prismjs' {
  const Prism: {
    highlight: (code: string, grammar: any, language: string) => string
    languages: Record<string, any>
    highlightAll: () => void
  }
  export default Prism
}
