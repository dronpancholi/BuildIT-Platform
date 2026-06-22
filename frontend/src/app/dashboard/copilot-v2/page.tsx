'use client';

import { useMutation } from '@tanstack/react-query';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';
import { useState } from 'react';

export default function CopilotV2Page() {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<Array<{ q: string; a: string; intents: string[]; completeness: string }>>([]);

  const askMutation = useMutation({
    mutationFn: (data: { question: string }) =>
      fetchApi(`/copilot-v2/ask?tenant_id=${MOCK_TENANT_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    onSuccess: (data: any) => {
      setHistory((prev) => [
        { q: question, a: data.data.answer, intents: data.data.intents_detected, completeness: data.data.data_completeness },
        ...prev,
      ]);
      setQuestion('');
    },
  });

  const handleAsk = () => {
    if (!question.trim()) return;
    askMutation.mutate({ question });
  };

  const suggestedQuestions = [
    'What campaigns are active and how are they performing?',
    'Which keywords should I focus on?',
    'What prospects have the highest authority?',
    'How are my citations performing?',
    'What should I do next?',
    'Why might my rankings be dropping?',
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">SEO Copilot</h1>
      <p className="text-gray-600">Ask questions about your SEO data. Answers cite real platform data.</p>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
          placeholder="Ask an SEO question..."
          className="flex-1 border rounded-lg px-4 py-2"
        />
        <button
          onClick={handleAsk}
          disabled={!question.trim() || askMutation.isPending}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg disabled:opacity-50"
        >
          {askMutation.isPending ? 'Thinking...' : 'Ask'}
        </button>
      </div>

      {/* Suggested */}
      {history.length === 0 && (
        <div className="space-y-2">
          <p className="text-sm text-gray-500">Suggested questions:</p>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((sq) => (
              <button
                key={sq}
                onClick={() => setQuestion(sq)}
                className="text-sm bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded-full"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* History */}
      <div className="space-y-4">
        {history.map((item, i) => (
          <div key={i} className="border rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 border-b">
              <span className="font-medium">Q: {item.q}</span>
              <span className="ml-2 text-xs text-gray-500">
                [{item.intents.join(', ')}] — data: {item.completeness}
              </span>
            </div>
            <div className="px-4 py-3 whitespace-pre-wrap text-sm">{item.a}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
