import wave

def save_wav(p_audio, channel, frame_rate, audio_format, buf, fileName):
    wf = wave.open(fileName, 'wb')
    wf.setnchannels(channel)
    wf.setsampwidth(p_audio.get_sample_size(audio_format))
    wf.setframerate(frame_rate)
    wf.writeframes(buf)
    wf.close()