import ObsidianEnvironment from '@/components/ObsidianEnvironment';

export const metadata = {
  title: 'CatLLM — Neural Interface',
  description: 'A premium AI assistant with RAG capabilities.',
};

export default function Page() {
  return (
    <main className="w-full min-h-screen bg-[#050508]">
      {/* The server delivers this shell instantly. 
        Once React hydrates on the client, the ObsidianEnvironment takes over 
        the DOM and begins the volumetric lighting cycles and state management. 
      */}
      <ObsidianEnvironment />
    </main>
  );
}
