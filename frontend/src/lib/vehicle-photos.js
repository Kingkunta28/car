import landCruiserPrado from "../images/Toyota Land Cruiser.png";
import landCruiserClassic from "../images/Toyota Land Cruiser.jpeg";
import harrier from "../images/Toyota G-Class.jpeg";
import rav4 from "../images/Toyota RAV4.jpeg";
import vanguard from "../images/Toyota RAV4_2.jpeg";
import rav4ThreeDoor from "../images/Toyota RAV4 2doors.jpeg";
import escudo from "../images/Toyota Escudo.jpg";
import grandVitara from "../images/Suzuki Escudo 2doors.jpeg";
import juke from "../images/Nissan E-Class.jpeg";
import ist from "../images/Toyota Ist.jpg";
import hilux from "../images/Toyota C-Class.jpeg";
import alphard from "../images/Toyota Alphard.jpeg";

// Keep the published fleet photos in Vercel's built frontend bundle. Database
// media URLs remain a fallback for vehicles added later in the admin.
const vehiclePhotos = {
  "toyota-land-cruiser-prado-2020": landCruiserPrado,
  "toyota-land-cruiser-prado-classic": landCruiserClassic,
  "toyota-harrier-2015": harrier,
  "toyota-rav4-2018": rav4,
  "toyota-vanguard-2018": vanguard,
  "toyota-rav4-2016-3-door": rav4ThreeDoor,
  "suzuki-escudo-2019": escudo,
  "suzuki-escudo-grand-vitara": grandVitara,
  "nissan-juke-2018": juke,
  "toyota-ist-2018": ist,
  "toyota-hilux": hilux,
  "toyota-alphard": alphard,
};

export default vehiclePhotos;
