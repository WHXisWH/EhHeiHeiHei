import { initializeApp } from "firebase/app";

const firebaseConfig = {
  apiKey: "AIzaSyAqEgrBzzWDn3lTvXGAWoIzr065AZMWHzA",
  authDomain: "parallelife.firebaseapp.com",
  projectId: "parallelife",
  storageBucket: "parallelife.firebasestorage.app",
  messagingSenderId: "808458124195",
  appId: "1:808458124195:web:a0fad4afc99d7f70123816"
};

export const app = initializeApp(firebaseConfig);
