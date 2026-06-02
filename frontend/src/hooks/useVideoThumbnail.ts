import { useEffect, useRef, useState } from "react";

const TIMEOUT_MS = 8000;

/**
 * Capture first frame from video stream URL; abort on unmount or URL change.
 */
export function useVideoThumbnail(streamUrl: string | null, enabled: boolean) {
  const [thumbUrl, setThumbUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!enabled || !streamUrl) {
      setThumbUrl(null);
      setFailed(false);
      setLoading(false);
      return;
    }

    let cancelled = false;
    const video = document.createElement("video");
    video.preload = "metadata";
    video.muted = true;
    video.playsInline = true;
    video.crossOrigin = "anonymous";
    video.src = streamUrl;

    const timer = window.setTimeout(() => {
      if (!cancelled) {
        setFailed(true);
        setLoading(false);
        cleanup();
      }
    }, TIMEOUT_MS);

    const cleanup = () => {
      video.removeAttribute("src");
      video.load();
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };

    const capture = () => {
      try {
        const w = video.videoWidth || 320;
        const h = video.videoHeight || 180;
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) throw new Error("no canvas");
        ctx.drawImage(video, 0, 0, w, h);
        canvas.toBlob(
          (blob) => {
            if (cancelled || !blob) return;
            if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
            objectUrlRef.current = URL.createObjectURL(blob);
            setThumbUrl(objectUrlRef.current);
            setFailed(false);
            setLoading(false);
          },
          "image/jpeg",
          0.85
        );
      } catch {
        if (!cancelled) {
          setFailed(true);
          setLoading(false);
        }
      }
    };

    video.addEventListener("loadeddata", () => {
      if (cancelled) return;
      video.currentTime = 0.1;
    });

    video.addEventListener("seeked", capture);
    video.addEventListener("error", () => {
      if (!cancelled) {
        setFailed(true);
        setLoading(false);
      }
    });

    setLoading(true);
    setFailed(false);
    setThumbUrl(null);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      cleanup();
    };
  }, [streamUrl, enabled]);

  return { thumbUrl, failed, loading };
}
