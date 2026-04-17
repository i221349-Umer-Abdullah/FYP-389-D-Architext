import { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";

import { connectDB } from "@/lib/db";
import User from "@/lib/models/User";

export const authOptions: NextAuthOptions = {
  session: { strategy: "jwt" },
  secret: process.env.NEXTAUTH_SECRET,

  pages: {
    signIn: "/auth",
    error: "/auth",
  },

  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),

    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const email = credentials.email.toLowerCase().trim();
        const password = credentials.password;

        await connectDB();
        const user = await User.findOne({ email });

        if (!user?.password) return null;

        const valid = await bcrypt.compare(password, user.password);
        if (!valid) return null;

        return {
          id: user._id.toString(),
          email: user.email,
          name: user.name,
          image: user.image ?? null,
        };
      },
    }),
  ],

  callbacks: {
    // Persist user id and Google profile info into the JWT on first sign-in
    async jwt({ token, user, account, profile }) {
      if (user) {
        token.id = user.id;
      }

      // On Google sign-in: upsert a user record in MongoDB
      if (account?.provider === "google" && profile?.email) {
        const googleProfile = profile as { name?: string; picture?: string; sub?: string };
        token.email = profile.email;
        token.name = googleProfile.name ?? profile.email;
        token.picture = googleProfile.picture ?? token.picture;

        await connectDB();
        const existing = await User.findOne({ email: profile.email.toLowerCase() });

        if (!existing) {
          const created = await User.create({
            email: profile.email.toLowerCase(),
            name: googleProfile.name ?? profile.email,
            password: null,
            provider: "google",
            googleId: googleProfile.sub ?? null,
            image: googleProfile.picture ?? null,
          });
          token.id = created._id.toString();
        } else {
          existing.name = googleProfile.name ?? existing.name;
          existing.googleId = googleProfile.sub ?? existing.googleId;
          existing.image = googleProfile.picture ?? existing.image;
          existing.provider = "google";
          await existing.save();
          token.id = existing._id.toString();
        }
      }

      return token;
    },

    async session({ session, token }) {
      if (session.user && token.id) {
        (session.user as typeof session.user & { id: string }).id = token.id as string;
      }
      return session;
    },
  },
};
