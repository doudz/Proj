import "@mdi/font/css/materialdesignicons.css";
import "vuetify/styles";
import { createVuetify } from "vuetify";

const ganttflowLight = {
  dark: false,
  colors: {
    background: "#F5F7FA",
    surface: "#FFFFFF",
    primary: "#1976D2",
    secondary: "#26A69A",
    success: "#66BB6A",
    warning: "#FFA726",
    error: "#EF5350",
    info: "#42A5F5",
  },
};

export default createVuetify({
  theme: {
    defaultTheme: "ganttflowLight",
    themes: { ganttflowLight },
  },
  defaults: {
    VBtn: { rounded: "lg" },
    VCard: { rounded: "lg" },
    VTextField: { variant: "outlined", density: "comfortable" },
    VSelect: { variant: "outlined", density: "comfortable" },
    VTextarea: { variant: "outlined", density: "comfortable" },
  },
});
