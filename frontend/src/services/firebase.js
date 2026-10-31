import { initializeApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyDC-RzT73KVHebhGMLFYlfNb5t8kpKxXqc",
  authDomain: "friday-ai-27647.firebaseapp.com",
  projectId: "friday-ai-27647",
  storageBucket: "friday-ai-27647.firebasestorage.app",
  messagingSenderId: "634753026307",
  appId: "1:634753026307:web:22470d67ad0ae46e44c136"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

export function getGuestId() {
  let gid = localStorage.getItem('friday_guest_id');
  if (!gid) {
    gid = 'guest_' + Math.random().toString(36).substring(2, 12);
    localStorage.setItem('friday_guest_id', gid);
  }
  return gid;
}

export async function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const user = auth.currentUser;
  if (user) {
    try {
      const token = await user.getIdToken();
      headers['Authorization'] = `Bearer ${token}`;
    } catch (e) {
      console.warn('Failed to obtain Firebase ID token', e);
    }
  } else {
    headers['X-Guest-ID'] = getGuestId();
  }
  return headers;
}

export async function loginWithGoogle() {
  return signInWithPopup(auth, googleProvider);
}

export async function loginWithEmail(email, password) {
  return signInWithEmailAndPassword(auth, email, password);
}

export async function registerWithEmail(email, password) {
  return createUserWithEmailAndPassword(auth, email, password);
}

export async function logoutUser() {
  return signOut(auth);
}

export function subscribeAuthState(callback) {
  return onAuthStateChanged(auth, callback);
}

