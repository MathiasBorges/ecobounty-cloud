// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getFirestore } from "firebase/firestore";

// Your web app's Firebase configuration
export const firebaseConfig = {
  apiKey: "YOUR_GOOGLE_CLOUD_OR_FIREBASE_API_KEY",
  authDomain: "ecobounty-9d250.firebaseapp.com",
  projectId: "ecobounty-9d250",
  storageBucket: "ecobounty-9d250.firebasestorage.app",
  messagingSenderId: "497537080035",
  appId: "1:497537080035:web:a403e448d9093feb1203d6",
  measurementId: "G-KXRY4KB64S"
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const analytics = typeof window !== "undefined" ? getAnalytics(app) : null;
export const db = getFirestore(app);

