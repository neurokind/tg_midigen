import os
import torch
import torch.nn as nn
import ai_utils.model_params
import math
import numpy as np
import pretty_midi
from miditoolkit import MidiFile

PREGEN_COUNT = 0


class MIDITokenizer:
    def __init__(self):
        self.event2idx = {}
        self.idx2event = {}
        self._build_vocab()


    def _build_vocab(self):
        # Events: notes, pauses, control events
        note_events = [f'NOTE_{i}' for i in range(128)]
        velocity_events = [f'VELOCITY_{i}' for i in range(128)]
        duration_events = [f'DURATION_{i}' for i in range(1, 7681)] # Ticks is in interval of 1--128
        control_events = [f'TIME_SHIFT', 'END_OF_TRACK']

        # Collecting all events
        all_events = note_events + velocity_events + duration_events + control_events

        # Create dicts
        self.event2idx = {event: idx for idx, event in enumerate(all_events)}
        self.idx2event = {idx: event for idx, event in enumerate(all_events)}

        self.vocab_size = len(all_events)


    def encode(self, midi_file):
        # Upload a .mid file
        midi = MidiFile(midi_file)
        notes = midi.instruments[0].notes

        # Sort notes by start time
        notes.sort(key=lambda x: (x.start, x.pitch))

        events = []
        current_time = 0

        for note in notes:
            # Time between previous and current events
            time_shift = note.start - current_time
            if time_shift > 0:
                events.append('TIME_SHIFT')
        
            # Add note, velocity & duration
            events.append(f'NOTE_{note.pitch}')
            events.append(f'VELOCITY_{note.velocity}')
            events.append(f'DURATION_{note.duration}')

            current_time = note.start

        events.append('END_OF_TRACK')

        result = []
        for event in events:
            result.append(self.event2idx[event])
        return result


    def decode(self, indices):
        events = [self.idx2event[event] for event in indices]

        # Create new .mid file
        midi = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)

        current_time = 0
        current_note = None
        current_velocity = None

        for event in events:
            if event.startswith('NOTE_'):
                current_note = int(event.split('_')[1])
            elif event.startswith('VELOCITY_'):
                current_velocity = int(event.split('_')[1])
            elif event.startswith('DURATION_'):
                if current_note is not None and current_velocity is not None:
                    duration = int(event.split('_')[1])
                    note = pretty_midi.Note(
                        velocity=current_velocity,
                        pitch=current_note,
                        start=current_time,
                        end=current_time + duration/100
                    )
                    instrument.notes.append(note)
                    current_time += duration/100
                    current_note = None
                    current_velocity = None
            elif event == 'TIME_SHIFT':
                current_time += 0.1 # Fixed time shift

        midi.instruments.append(instrument)
        return midi


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        x = x + self.pe[:x.size(0)]
        return self.dropout(x)
    

class MusicTransformer(nn.Module):
    def __init__(self, vocab_size, d_model, n_heads, num_layers, d_ff, dropout):
        super().__init__()
        self.d_model = d_model
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_encoder = PositionalEncoding(d_model, dropout)
        
        encoder_layers = nn.TransformerEncoderLayer(d_model, n_heads, d_ff, dropout)
        self.transformer = nn.TransformerEncoder(encoder_layers, num_layers)
        
        self.fc_out = nn.Linear(d_model, vocab_size)

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    def forward(self, src, src_mask=None, src_key_padding_mask=None):
        src = self.embedding(src) * math.sqrt(self.d_model)
        src = self.pos_encoder(src)
        
        output = self.transformer(src, src_mask, src_key_padding_mask)
        output = self.fc_out(output)
        return output

def load_model(model_path, tokenizer):
    model = MusicTransformer(
        vocab_size=tokenizer.vocab_size,
        d_model=ai_utils.model_params.d_model,
        n_heads=ai_utils.model_params.n_heads,
        num_layers=ai_utils.model_params.num_layers,
        d_ff=ai_utils.model_params.d_ff,
        dropout=ai_utils.model_params.dropout
    ).to('cuda' if torch.cuda.is_available() else 'cpu')
    
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu'), weights_only=False))
    model.eval()
    return model


def generate_sample(model, tokenizer, temperature=1.2, max_len=512):
    model.eval()
    with torch.no_grad():
        # Random note as starting token
        current_token = torch.tensor([[np.random.randint(0, 128)]], device=model.device)
        generated = [current_token.item()]
        
        for _ in range(max_len):
            # Убираем лишнюю размерность (unsqueeze(0) уже есть в создании тензора)
            output = model(current_token)  # теперь форма [1, 1]
            
            # Получаем последний выход (форма [1, vocab_size])
            output = output[:, -1, :] / temperature
            probs = torch.softmax(output, dim=-1)
            
            next_token = torch.multinomial(probs, num_samples=1)
            generated.append(next_token.item())
            
            if next_token.item() == tokenizer.event2idx['END_OF_TRACK']:
                break
                
            current_token = next_token
        
        # Decode
        midi = tokenizer.decode(generated)
        return midi

        
def generate_midi(temperature=1.2):
    global PREGEN_COUNT
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # --- PREGEN LOGIC ---
    pregen_dir = os.path.join(current_dir, 'pregen')
    pregen_files = [f"{i}.mid" for i in range(8)]
    if PREGEN_COUNT < len(pregen_files):
        midi_path = os.path.join(pregen_dir, pregen_files[PREGEN_COUNT])
        PREGEN_COUNT += 1
        return pretty_midi.PrettyMIDI(midi_path)
    # --- END PREGEN LOGIC ---

    # Load tokenizer and model from the ai_utils directory
    tokenizer_path = os.path.join(current_dir, 'tokenizer.pt')
    model_path = os.path.join(current_dir, 'transformer_epoch_7.pt')
    
    try:
        # Попробуем загрузить токенизатор с явным указанием класса
        import sys
        sys.modules['__main__'] = sys.modules[__name__]
        tokenizer = torch.load(tokenizer_path, weights_only=False, map_location='cpu')
    except Exception as e:
        print(f"Ошибка загрузки токенизатора: {e}")
        # Создаем новый токенизатор если загрузка не удалась
        tokenizer = MIDITokenizer()
    
    model = load_model(model_path, tokenizer)
    midi = generate_sample(model, tokenizer, temperature=temperature)
    return midi
